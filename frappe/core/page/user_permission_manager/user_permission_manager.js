frappe.pages['user-permission-manager'].on_page_load = function(wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'User Permission Manager',
		single_column: true
	});

	const user_permission_manager_wrapper = $("<div class='user-perm-engine'></div>").appendTo(page.main);

	let user_permission_manager = null;

	frappe.call({
		module:'frappe.core',
		page:'user_permission_manager',
		method: 'get_all_users',
		callback: function(r) {
			const users = r.message.users;
			this.user_select = page.add_select(__('User'), [{value: '', label: __('Select User') + '...'}]
				.concat(users))
				.change(function() {
					frappe.set_route('user-permission-manager', $(this).val());
					if (!user_permission_manager) {
						user_permission_manager = new frappe.UserPermissionManager(
							user_permission_manager_wrapper,
							$(this).val()
						);
					} else {
						user_permission_manager.UserPermissionManagerEngine.user = $(this).val();
					}
				});
			let route_user = frappe.get_route()[1];
			if (route_user) {
				this.user_select.val(route_user).change();

			}
		}
	});

};