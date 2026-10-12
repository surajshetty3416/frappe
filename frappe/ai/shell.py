# Copyright (c) 2026, Frappe Technologies and contributors
# License: MIT. See LICENSE

import frappe


def get_boot() -> dict:
	if frappe.session.user == "Guest":
		return {}

	from frappe.ai.api import boot
	from frappe.ai.artifacts import artifact_types

	return {"flow_boot": boot(), "studio_artifacts": artifact_types()}


def make_chat_the_home():
	"""A new site opens on Studio, where people ask for websites, dashboards and apps."""
	if not frappe.db.get_single_value("System Settings", "default_app"):
		frappe.db.set_single_value("System Settings", "default_app", "studio")
