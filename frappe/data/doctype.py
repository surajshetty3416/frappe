import frappe


def show_title_in_link(doc, method=None):
	if doc.custom and doc.title_field:
		doc.show_title_field_in_link = 1


def grant_named_rights(doc, method=None):
	"""A permission row an agent writes grants only the rights it names; DocPerm's defaults would add read, write, delete and more."""
	for perm in doc.permissions:
		for right in rights():
			if perm.get(right) is None:
				perm.set(right, 0)


def describe_rights(doc, method=None):
	return {
		"permissions": {
			perm.role if not perm.permlevel else f"{perm.role} (level {perm.permlevel})": [
				right for right in rights() if perm.get(right)
			]
			for perm in doc.permissions
		}
	}


def rights() -> list[str]:
	return [df.fieldname for df in frappe.get_meta("DocPerm").fields if df.fieldtype == "Check"]
