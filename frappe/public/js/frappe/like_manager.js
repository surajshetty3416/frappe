class Like extends HTMLElement {
	constructor() {
		super();
		this.attachShadow({mode: 'open'});
		this.doctype = this.getAttribute('reference-doctype');
		this.docname = this.getAttribute('reference-docname');

	}

	async connectedCallback() {
		this.setup_like_listener();
		this.like_wrapper = $(`<div class="like"><span> 👍 </span></div>`);
		this.counter = $(`<span class="counter"><span>`);
		this.like_wrapper.append(this.counter);
		this.shadowRoot.innerHTML = `
			<style>
				.like {
					font-size: var(--text-sm);
					cursor: pointer;
				}
				.liked {
					padding: 0px 5px;
					border-radius: 10px;
					border: 1px solid var(--blue-500);
					background: vat(--blue-50)
				}
			</style>
		`;

		this.like_wrapper.appendTo($(this.shadowRoot));
		await this.get_likes();
		this.set_likes();
		this.setup_events();
	}

	disconnectedCallback() {
		//implementation
	}

	attributeChangedCallback(name, oldVal, newVal) {
		//implementation
	}

	adoptedCallback() {
		//implementation
	}

	get_likes() {
		return frappe.xcall('frappe.core.doctype.document_like.document_like.get_likes', {
			'reference_doctype': this.doctype,
			'reference_docname': this.docname
		}).then(likes => {
			if (likes.find(liker => liker === frappe.session.user)) {
				this.liked = true;
			}
			this.likes = likes;
		});
	}

	setup_like_listener() {
		frappe.realtime.on(`document-like-${this.doctype}-${this.docname}`, (res) => {
			if (res.owner !== frappe.session.user) {
				this.update_likes(!res.unlike, res.owner);
			}
			this.set_likes();
		});
	}

	setup_events() {
		this.like_wrapper.click(() => {
			this.update_likes(!this.liked);
			this.set_likes();
			frappe.xcall('frappe.core.doctype.document_like.document_like.toggle_like', {
				'reference_doctype': this.doctype,
				'reference_docname': this.docname
			}).then(() => {});
		});
	}

	set_likes() {
		this.like_wrapper.toggleClass('liked', !!this.liked);

		this.counter.toggle(this.likes.length > 0);
		if (this.likes.length) {
			this.counter.text(this.likes.length);
		}
	}

	update_likes(like, user) {
		user = user || frappe.session.user;
		if (like) {
			this.likes.push(user);
		} else {
			this.likes = this.likes.filter(l => l !== user);
		}
		this.liked = this.likes.includes(frappe.session.user);
	}

}

window.customElements.define('frappe-like', Like);