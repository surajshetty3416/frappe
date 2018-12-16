import Vue from 'vue/dist/vue.js';
import UserPermissionManagerEngine from './UserPermissionManagerEngine.vue';

frappe.UserPermissionManager = class {
	constructor(wrapper, user) {
		this.wrapper = wrapper;
		this.user = user;
		this.make();
	}
	make() {
		this.UserPermissionManagerEngine = new Vue({
			el: this.wrapper[0],
			render: h => h(UserPermissionManagerEngine, {
				props: {
					'user': this.user
				}
			}),

		});
	}
};