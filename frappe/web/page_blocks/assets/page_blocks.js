(function () {
	if (window.fbPageBlocksWired) return;
	window.fbPageBlocksWired = true;

	const FAILED = "Something went wrong. Try again.";

	async function call(method, args, httpMethod) {
		const options = { method: httpMethod || "POST", headers: { Accept: "application/json" } };
		let url = "/api/method/" + method;
		if (options.method === "GET") {
			url += "?" + new URLSearchParams(args);
		} else {
			options.headers["Content-Type"] = "application/json";
			const token = window.frappe && window.frappe.csrf_token;
			if (token && token !== "None") options.headers["X-Frappe-CSRF-Token"] = token;
			options.body = JSON.stringify(args);
		}
		const response = await fetch(url, options);
		const data = await response.json().catch(() => ({}));
		if (response.status === 429) throw new Error("Too many requests. Wait a few minutes and try again.");
		if (!response.ok) throw new Error(serverMessage(data) || FAILED);
		return data.message;
	}

	function serverMessage(data) {
		try {
			const messages = JSON.parse(data._server_messages || "[]");
			const last = JSON.parse(messages[messages.length - 1] || "null");
			const div = document.createElement("div");
			div.innerHTML = (last && last.message) || "";
			return div.textContent.trim();
		} catch (e) {
			return "";
		}
	}

	// --- form block ---

	function fieldMessage(input) {
		const v = input.validity;
		if (v.valueMissing) return input.type === "checkbox" ? "Tick this box to continue." : "This field is required.";
		if (v.typeMismatch && input.type === "email") return "Enter a valid email address.";
		if (v.typeMismatch && input.type === "url") return "Enter a full link, starting with https://.";
		if (v.badInput || v.stepMismatch) return "Enter a valid value.";
		if (v.tooLong) return "This is too long.";
		return input.validationMessage;
	}

	function wireForm(form) {
		const fields = Array.from(form.querySelectorAll("[data-field]"));
		const formError = form.querySelector(".fb-form-error");
		const button = form.querySelector(".fb-submit");
		const inputOf = (field) => field.querySelector("[name]");
		const showError = (field, message) => {
			const error = field.querySelector(".fb-error");
			error.textContent = message || "";
			error.hidden = !message;
			inputOf(field).setAttribute("aria-invalid", message ? "true" : "false");
		};
		const showFormError = (message) => {
			formError.textContent = message || "";
			formError.hidden = !message;
		};
		fields.forEach((field) => {
			const clear = () => showError(field, "");
			inputOf(field).addEventListener("input", clear);
			inputOf(field).addEventListener("change", clear);
		});

		form.addEventListener("submit", async (event) => {
			event.preventDefault();
			showFormError("");
			let firstInvalid = null;
			fields.forEach((field) => {
				const input = inputOf(field);
				const valid = input.checkValidity();
				showError(field, valid ? "" : fieldMessage(input));
				if (!valid && !firstInvalid) firstInvalid = input;
			});
			if (firstInvalid) return firstInvalid.focus();

			const values = {};
			fields.forEach((field) => {
				const input = inputOf(field);
				values[input.name] = input.type === "checkbox" ? (input.checked ? 1 : 0) : input.value;
			});
			button.disabled = true;
			try {
				const result = await call("frappe.web.page_blocks.form.submit", {
					page: form.dataset.page,
					block: form.dataset.block,
					values: values,
					company_website: form.querySelector(".fb-honeypot input").value,
				});
				if (!result.ok) {
					Object.entries(result.errors || {}).forEach(([name, message]) => {
						const field = fields.find((f) => f.dataset.field === name);
						if (field) showError(field, message);
					});
					const invalid = fields.find((f) => inputOf(f).getAttribute("aria-invalid") === "true");
					if (invalid) inputOf(invalid).focus();
					showFormError(result.message);
					return;
				}
				if (result.route) return window.location.assign(result.route);
				const success = form.nextElementSibling;
				form.hidden = true;
				success.hidden = false;
				success.focus();
			} catch (error) {
				showFormError(error.message);
			} finally {
				button.disabled = false;
			}
		});
	}

	// --- chat block ---

	function escapeHtml(text) {
		return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
	}

	function inline(text) {
		return escapeHtml(text)
			.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
			.replace(/`([^`]+)`/g, "<code>$1</code>")
			.replace(/\[([^\]]+)\]\(((?:https?:\/\/|\/)[^)\s]*)\)/g, '<a href="$2">$1</a>');
	}

	function markdown(text) {
		const ITEM = /^\s*(?:[-*]|\d+\.)\s+/;
		return text
			.trim()
			.split(/\n\s*\n/)
			.map((part) => {
				const lines = part.split("\n").filter((line) => line.trim());
				if (lines.length && lines.every((line) => ITEM.test(line))) {
					const tag = /^\s*\d+\./.test(lines[0]) ? "ol" : "ul";
					return "<" + tag + ">" + lines.map((l) => "<li>" + inline(l.replace(ITEM, "")) + "</li>").join("") + "</" + tag + ">";
				}
				return "<p>" + lines.map(inline).join("<br>") + "</p>";
			})
			.join("");
	}

	function wireChat(root) {
		const page = root.dataset.page;
		const block = root.dataset.block;
		const key = "fb-chat:" + page + ":" + block;
		const log = root.querySelector(".fb-chat-log");
		const typing = root.querySelector(".fb-chat-typing");
		const composer = root.querySelector(".fb-chat-composer");
		const input = root.querySelector(".fb-chat-input");
		const sendButton = root.querySelector(".fb-chat-send");
		let conversation = null;
		let since = 0;
		let busy = false;
		try {
			conversation = JSON.parse(localStorage.getItem(key) || "null");
		} catch (e) {
			conversation = null;
		}

		const scrollDown = () => (log.scrollTop = log.scrollHeight);
		const add = (role, text) => {
			const message = document.createElement("div");
			message.className = "fb-chat-msg fb-chat-" + role;
			if (role === "agent") message.innerHTML = markdown(text);
			else message.textContent = text;
			log.insertBefore(message, typing);
			scrollDown();
		};
		const setBusy = (value) => {
			busy = value;
			typing.hidden = !value;
			sendButton.disabled = value || !input.value.trim();
			scrollDown();
		};
		const resize = () => {
			input.style.height = "auto";
			input.style.height = Math.min(input.scrollHeight, 120) + "px";
			sendButton.disabled = busy || !input.value.trim();
		};

		async function follow(restoring) {
			setBusy(true);
			try {
				for (;;) {
					const result = await call(
						"frappe.web.page_blocks.chat.poll",
						{ page: page, block: block, session: conversation.session, token: conversation.token, since: since },
						"GET"
					);
					result.messages.forEach((m) => {
						if (m.role !== "visitor" || restoring) add(m.role, m.text);
					});
					since = result.seq;
					restoring = false;
					if (!result.running) break;
					await new Promise((resolve) => setTimeout(resolve, 1000));
				}
			} catch (error) {
				if (restoring) {
					localStorage.removeItem(key);
					conversation = null;
				} else {
					add("error", error.message);
				}
			} finally {
				setBusy(false);
			}
		}

		composer.addEventListener("submit", async (event) => {
			event.preventDefault();
			const text = input.value.trim();
			if (!text || busy) return;
			input.value = "";
			resize();
			add("visitor", text);
			setBusy(true);
			try {
				const result = await call("frappe.web.page_blocks.chat.send", {
					page: page,
					block: block,
					message: text,
					session: conversation ? conversation.session : null,
					token: conversation ? conversation.token : null,
				});
				conversation = { session: result.session, token: result.token };
				localStorage.setItem(key, JSON.stringify(conversation));
			} catch (error) {
				add("error", error.message);
				return setBusy(false);
			}
			await follow(false);
		});
		input.addEventListener("input", resize);
		input.addEventListener("keydown", (event) => {
			if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
				event.preventDefault();
				composer.requestSubmit();
			}
		});
		resize();
		if (conversation) follow(true);
	}

	function wire() {
		document.querySelectorAll("[data-fb-form]").forEach(wireForm);
		document.querySelectorAll("[data-fb-chat]").forEach(wireChat);
	}

	if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", wire);
	else wire();
})();
