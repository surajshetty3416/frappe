import frappe
from frappe import _

@frappe.whitelist()
def get_all_users():
	frappe.only_for("System Manager")

	users = frappe.db.sql("""select name, full_name as fullname
		from tabUser where enabled=1 and user_type!="Website User" """, as_dict=1)

	user_list = [{"label":_(user.get("fullname")), "value":user.get("name")} for user in users]

	return {
		"users": sorted(user_list, key=lambda d: d['label'])
	}