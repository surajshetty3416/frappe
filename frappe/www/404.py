# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: MIT. See LICENSE

from frappe.web.not_found import use_builder_page


def get_context(context):
	context.http_status_code = 404
	use_builder_page(context)
