import { presentEvent } from "./events.js";
import { SessionStream } from "./stream.js";

const IMAGE_FILE = /\.(png|jpe?g|gif|webp|bmp)$/i;

const contextBlock = (context) => `\n\n<studio_context>\n${JSON.stringify(context)}\n</studio_context>`;

// The store's client surface over frappe.ai.api. Sessions are Flow Session docs, models are
// Flow Model docs (the daemon's provider ids are mapped back to them), attachments are
// private Files staged through attach_file. `transport` is the page's Frappe transport
// (frappe.js); `hooks` mirror what the server reports about a session.
export class FrappeClient {
	constructor({ socket, boot, transport, hooks = {} }) {
		this.socket = socket;
		this.hooks = hooks;
		this.transport = transport;
		this.configs = new Map(); // session → the config the store last saw
		this.fileIds = new Map(); // file name → the File it was staged as, for this page
		this.setModels(boot?.models ?? []);
	}

	setModels(models) {
		this.modelRows = models;
		this.modelByProviderId = new Map(models.map((m) => [m.model_id, m.name]));
		this.contextWindows = new Map(models.map((m) => [m.name, m.context_window || null]));
	}

	present(event, sid = event.session_id) {
		return presentEvent(event, {
			fileId: (name, fallback) => this.fileIds.get(name) ?? fallback ?? `file:${name}`,
			modelName: (id) => {
				const selected = this.configs.get(sid)?.model;
				const model = this.modelRows.find((row) => row.name === selected);
				return model?.model_id === id ? selected : this.modelByProviderId.get(id) ?? id;
			},
		});
	}

	// --- sessions --------------------------------------------------------------

	async session(sid) {
		const data = await this.transport.call("frappe.ai.api.session", { session: sid });
		this.hooks.onSession?.(data);
		return this.sessionInfo(data);
	}

	sessionInfo(data) {
		const config = {
			auto_approve: data.auto_approve,
			title: data.title,
			agent: data.agent,
			model: data.model,
		};
		this.configs.set(data.name, config);
		return {
			session_id: data.name,
			title: data.title,
			agent: data.agent,
			model: data.model,
			latest_seq: 0,
			context_window: this.contextWindows.get(data.model) ?? null,
			config,
		};
	}

	async createSession(config = {}) {
		const data = await this.transport.call("frappe.ai.api.create_session", {
			auto_approve: config.auto_approve ? 1 : 0,
		});
		this.hooks.onSession?.(data);
		return {
			session_id: data.name,
			config: { ...this.sessionInfo(data).config, model: data.model },
		};
	}

	async entries(sid, since = 0, path = "active") {
		const data = await this.transport.call("frappe.ai.api.entries", { session: sid, since, path });
		const entries = (data.entries ?? []).map((row) => this.present(row, sid));
		return {
			...data,
			entries,
			preview: (data.preview ?? []).map((row) => this.present(row, sid)),
		};
	}

	stream(sid, since = 0) {
		return new SessionStream({
			socket: this.socket,
			session: sid,
			since,
			fetchEntries: (cursor) => this.entries(sid, cursor, "all"),
			present: (event) => this.present(event, sid),
			onTerminal: () => this.syncSession(sid),
		});
	}

	async syncSession(sid) {
		const data = await this.transport.call("frappe.ai.api.sync_session", { session: sid });
		this.hooks.onSession?.(data);
		return data;
	}

	// `context` is what the editor beside the chat shows (see the shell's context.ts); the agent
	// reads it as JSON after the message, and events.js turns it back into chips
	async run(sid, message, attachments = [], context = null) {
		if (context) message = `${message}${contextBlock(context)}`;
		return this.transport.call("frappe.ai.api.run", { session: sid, message, attachments });
	}

	resume(sid, seq, answers) {
		return this.transport.call("frappe.ai.api.resume", {
			session: sid,
			answers,
			approval_seq: seq,
		});
	}

	abort(sid) {
		return this.transport.call("frappe.ai.api.abort", { session: sid });
	}

	cancelPending(sid) {
		return this.transport.call("frappe.ai.api.cancel_pending", { session: sid });
	}

	async patchConfig(sid, patch) {
		const config = { ...(this.configs.get(sid) ?? {}) };
		if ("title" in patch) {
			const data = await this.transport.call("frappe.ai.api.set_title", {
				session: sid,
				title: patch.title,
			});
			config.title = data.title;
		}
		if ("auto_approve" in patch) {
			const data = await this.transport.call("frappe.ai.api.set_auto_approve", {
				session: sid,
				auto_approve: patch.auto_approve ? 1 : 0,
			});
			config.auto_approve = data.auto_approve;
		}
		this.configs.set(sid, config);
		return { config };
	}

	deleteSession(sid) {
		return this.transport.call("frappe.ai.api.delete_session", { session: sid });
	}

	// --- attachments -----------------------------------------------------------

	async prepareAttachment(file, model) {
		const uploaded = await this.transport.uploadFile(file);
		try {
			const staged = await this.transport.call("frappe.ai.api.attach_file", {
				file: uploaded.name,
				model,
			});
			this.fileIds.set(staged.file_name, staged.file);
			return {
				id: staged.file,
				name: staged.file_name,
				kind: IMAGE_FILE.test(staged.file_name) ? "image" : "file",
			};
		} catch (error) {
			await this.discardAttachments([uploaded.name]).catch(() => {});
			throw error;
		}
	}

	discardAttachments(ids) {
		return this.transport.call("frappe.ai.api.cleanup_attachments", { attachments: ids });
	}

	async uploadAttachments(_sid, files) {
		const attachments = [];
		try {
			for (const file of files) attachments.push(await this.prepareAttachment(file));
			return { attachments };
		} catch (error) {
			await this.discardAttachments(attachments.map((item) => item.id)).catch(() => {});
			throw error;
		}
	}

	cleanupAttachments(sid, ids) {
		return this.transport.call("frappe.ai.api.cleanup_attachments", {
			session: sid,
			attachments: ids,
		});
	}

	// --- skills ----------------------------------------------------------------

	// the store asks a live session, or previews the assistant a new chat starts with
	skills(sid) {
		return this.transport.call("frappe.ai.api.skills", { session: sid });
	}

	previewSkills() {
		return this.transport.call("frappe.ai.api.skills");
	}
}
