# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: MIT. See LICENSE

"""The page behind every layer's route (/flow, /builder, /insights, /studio): the built
frontend shell, with each layer's boot data rendered into it."""

import frappe
from frappe import _
from frappe.translate import get_all_translations

no_cache = 1


def get_context(context):
	context.boot = get_boot()


@frappe.whitelist(methods=["POST"], allow_guest=True)
def get_context_for_dev() -> dict:
	"""The same boot data for the Vite dev server, which cannot render the page template."""
	if not frappe.conf.developer_mode:
		frappe.throw(_("Only available in developer mode."), frappe.PermissionError)
	return get_boot()


def get_boot() -> dict:
	csrf_token = frappe.sessions.get_csrf_token()
	frappe.db.commit()  # the token is written to the session on first use, as /desk does
	boot = {
		"csrf_token": csrf_token,
		"site_name": frappe.local.site,
		"socketio_port": frappe.conf.socketio_port,
		"is_developer_mode": bool(frappe.conf.developer_mode),
		"translated_messages": get_all_translations(frappe.local.lang),
	}
	for layer in frappe.get_hooks("layers"):
		boot.update(frappe.get_attr(f"frappe.{layer}.shell.get_boot")())
	return boot
