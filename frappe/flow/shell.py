# Copyright (c) 2026, Frappe Technologies and contributors
# License: MIT. See LICENSE

import frappe


def get_boot() -> dict:
	if frappe.session.user == "Guest":
		return {}

	from frappe.flow.api import boot

	return {"flow_boot": boot()}
