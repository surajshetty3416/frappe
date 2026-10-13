import frappe
from frappe.model import no_value_fields, table_fields


@frappe.whitelist()
def get_schema() -> list[dict]:
	"""The site's custom DocTypes, their child tables nested, and the core DocTypes they link to."""
	frappe.has_permission("DocType", "read", throw=True)
	custom = frappe.get_all("DocType", filters={"custom": 1}, pluck="name", order_by="creation asc")
	nodes = {name: describe(name, core=False) for name in custom}
	for node in list(nodes.values()):
		for field in node["fields"]:
			target = field["options"]
			if field["fieldtype"] == "Link" and target and target not in nodes:
				nodes[target] = describe(target, core=True)
	return list(nodes.values())


def describe(doctype: str, core: bool) -> dict:
	meta = frappe.get_meta(doctype)
	counted = not (meta.istable or meta.issingle)
	return {
		"name": doctype,
		"core": core,
		"istable": meta.istable,
		"count": frappe.db.count(doctype) if counted else None,
		"fields": []
		if core
		else [
			{
				"fieldname": field.fieldname,
				"label": field.label,
				"fieldtype": field.fieldtype,
				"options": field.options,
				"reqd": field.reqd,
			}
			for field in meta.fields
			if field.fieldtype not in no_value_fields or field.fieldtype in table_fields
		],
	}
