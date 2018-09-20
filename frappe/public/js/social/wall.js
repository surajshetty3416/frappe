import Vue from 'vue/dist/vue.js';

// components
import Wall from './Wall.vue';
import SocialSidebar from './SocialSidebar.vue';
frappe.provide('frappe.social');

frappe.social.Wall = class WallFeed {
	constructor({ parent }) {
		this.$parent = $(parent);
		this.page = parent.page;
		this.setup_header();
		this.make_sidebar();
		this.make_body();
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
			render: h => h(SocialSidebar)
		});
	}
	setup_header() {
		this.page.set_title(__('Social'));
	}
};