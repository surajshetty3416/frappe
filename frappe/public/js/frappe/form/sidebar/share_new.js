import ShareVue from "./Share.vue";

frappe.ui.form.Share2 = class Share {
	constructor({ parent, frm }) {
		this.parent = parent;
		this.frm = frm;
		// this.make();
		this.make_vue();
	}
	refresh() {

	}
	make_vue() {
		this.share_dialog = new frappe.ui.Dialog({
			title: __("Share"),
		});
		let $vm = new Vue({
			el: this.share_dialog.body,
			render: h =>
				h(ShareVue, {
					props: {
						frm: this.frm
					}
				})
		});
		this.show();
	}

	show() {
		this.share_dialog.show();
	}
	make() {
		this.share_dialog = new frappe.ui.Dialog({
			title: __("Share"),
			fields: [{
				fieldtype: "Link",
				fieldname: "share_with",
				label: __("Share With"),
				options: "User"
			}, {
				fieldtype: "HTML",
				fieldname: "share_options"
			}]
		});
		this.share_dialog.get_field("share_options").$wrapper.append(frappe.render_template('share', {
			shared_with: [{
				user: "suraj@erpnext.com",
				can_share: true,
				rights: "Can Read"
			}, {
				user: "faris@erpnext.com",
				can_share: true,
				rights: "Can Write"
			}],
			rights_options: [{
				label: "Can Read",
				value: "can_read"
			}, {
				label: "Can Write",
				value: "can_write"
			}, {
				label: "Can Share",
				value: "can_share"
			}],
			actions: [{
				label: "Delete",
				value: "delete"
			}]
		}));
		this.setup_events();
		this.show();
	}
	setup_events() {
		this.parent.find(".share-doc-btn").click(() => {
			this.show();
		});
	}

	update_share(share_obj) {
		const args = {
			doctype: this.doctype,
			name: this.doc.name,
			notify: 1,
		};

		args.user = share_obj.user;

		if (share_obj.can_read) {
			args.read = true;
		} else if (share_obj.can_write) {
			args.write = true;
		} else if (share_obj.can_submit) {
			args.submit = true;
		}

		frappe.call({
			method: "frappe.share.add",
			args,
			btn: this,
			callback: (r) => {
				$.each(this.shared, (i, s) => {
					if (s && s.user === r.message.user) {
						// re-adding / remove the old share rule.
						delete this.shared[i];
					}
				})
				this.dirty = true;
				this.shared.push(r.message);
				this.render_shared();
				this.shared.refresh();
			}
		});
	}
};