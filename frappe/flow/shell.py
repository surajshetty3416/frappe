# Copyright (c) 2026, Frappe Technologies and contributors
# License: MIT. See LICENSE

import frappe


def get_boot() -> dict:
	if frappe.session.user == "Guest":
		return {}

	from frappe.flow.api import boot

	return {"flow_boot": boot()}


def make_chat_the_home():
	"""A new site opens on the chat, where people ask for websites, dashboards and apps."""
	if not frappe.db.get_single_value("System Settings", "default_app"):
		frappe.db.set_single_value("System Settings", "default_app", "flow")
