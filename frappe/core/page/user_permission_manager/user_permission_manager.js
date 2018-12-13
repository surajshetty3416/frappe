frappe.pages['user-permission-manager'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'User Permission Manager',
		single_column: true
	});
	this.user_permission_manager_wrapper = $("<div class='user-perm-engine'></div>").appendTo(page.main);
	frappe.call({
		module:'frappe.core',
		page:'user_permission_manager',
		method: 'get_all_users',
		callback: function(r) {
			setup_page(r.message);
		}
	});
	const me = this;
	function setup_page(options) {
		this.doctype_select = page.add_select(__('User'), [{value: '', label: __('Select User') + '...'}]
			.concat(options.users))
			.change(function() {
				frappe.set_route('user-permission-manager', $(this).val());
				console.log(me.user_permission_manager_wrapper);
				new frappe.UserPermissionManager(me.user_permission_manager_wrapper, $(this).val());
			});
	}
};