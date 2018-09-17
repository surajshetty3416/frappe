import Vue from 'vue/dist/vue.js';

// components
import Wall from './Wall.vue';
frappe.provide('frappe.social');

frappe.social.Wall = class WallFeed {
	constructor({ parent }) {
		this.$parent = $(parent);
		this.page = parent.page;
		this.make_body();
		this.setup_header();
	}
	make_body() {
		this.$body = this.$parent.find('.layout-main-section');
		this.$page_container = $('<div class="wall-container">').appendTo(this.$body);

		new Vue({
			el: '.wall-container',
			render: h => h(Wall)
		});
	}
	setup_header() {
		this.page.set_title(__('Wall'));
	}
};