import Vue from 'vue/dist/vue.js';

// components
import Wall from './Wall.vue';
import WallSidebar from './WallSidebar.vue';
frappe.provide('frappe.social');

frappe.social.Wall = class WallFeed {
	constructor({ parent }) {
		this.$parent = $(parent);
		this.page = parent.page;
		this.setup_header();
		this.make_sidebar();
		this.make_body();
		this.set_primary_action();
	}
	make_body() {
		this.$body = this.$parent.find('.layout-main-section');
		this.$page_container = $('<div class="wall-container">').appendTo(this.$body);

		new Vue({
			el: '.wall-container',
			render: h => h(Wall)
		});
	}
	make_sidebar() {
		this.$sidebar = this.$parent.find('.layout-side-section');

		new Vue({
			el: $('<div>').appendTo(this.$sidebar)[0],
			render: h => h(WallSidebar)
		});
	}
	setup_header() {
		this.page.set_title(__('Social'));
	}
	set_primary_action() {
		this.page.set_primary_action(__('Post'), () => {
			frappe.social.post_dialog.show();
		});
	}
};

frappe.social.post_dialog = new frappe.ui.Dialog({
	title: __("Create A Post"),
	fields: [
		{fieldtype: "Text Editor", fieldname: "content", label: __("Content"), reqd: 1},
	]
});

frappe.social.post_dialog.set_primary_action(__('Post'), () => {
	const values = frappe.social.post_dialog.get_values();
	const post = frappe.model.get_new_doc('Post');
	post.content = values.content;
	frappe.db.insert(post).then(() => {
		frappe.social.post_dialog.clear();
		frappe.social.post_dialog.hide();
	});
});