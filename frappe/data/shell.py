import frappe


def get_boot() -> dict:
	if frappe.session.user == "Guest":
		return {}
	return {"field_types": frappe.get_meta("DocField").get_field("fieldtype").options.split("\n")}
