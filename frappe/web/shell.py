import frappe
from frappe.builder.hooks import builder_path
from frappe.integrations.frappe_providers.frappecloud_billing import is_fc_site
from frappe.pulse.utils import get_app_version


def get_boot() -> dict:
	return {
		"builder_path": f"/{builder_path}",
		"builder_version": get_app_version("frappe"),
		"is_fc_site": is_fc_site(),
		"is_read_only_mode": bool(frappe.flags.read_only),
	}
