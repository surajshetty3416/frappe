import frappe


def get_boot() -> dict:
	return {"site_url": frappe.utils.get_site_url(frappe.local.site)}
