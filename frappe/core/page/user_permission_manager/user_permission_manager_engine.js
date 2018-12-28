import Vue from 'vue/dist/vue.js';
import UserPermissionManagerEngine from './UserPermissionManagerEngine.vue';

frappe.UserPermissionManager = class {
	constructor(wrapper, user) {
		this.wrapper = wrapper;
		this.user = user;
		this.make(this.user);
	}
	make(user) {
		this.UserPermissionManagerEngine = new Vue({
			el: this.wrapper[0],
			data() {
				return {
					user
				};
			},
			render(h) {
				return h(UserPermissionManagerEngine, {
					props: {
						'user': this.user
					}
				});
			}

		});
	}
};