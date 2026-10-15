import frappe
from frappe.ai.artifacts import artifact_rows, own_chats
from frappe.ai.doctype.studio_project.studio_project import add_artifact
from frappe.utils import now


# Studio starts from a project now. Each person's chats from before projects, and what they made,
# go into a project of theirs.
def execute():
	sessions = frappe.get_all(
		"Flow Session",
		filters=[["project", "is", "not set"], *[f for f in own_chats() if f[0] != "owner"]],
		fields=["name", "owner"],
	)
	by_owner = {}
	for session in sessions:
		by_owner.setdefault(session.owner, []).append(session.name)
	for owner, names in by_owner.items():
		project = frappe.get_doc(
			{"doctype": "Studio Project", "title": "General", "owner": owner, "creation": now()}
		).insert(ignore_permissions=True)
		frappe.db.set_value(
			"Flow Session", {"name": ("in", names)}, "project", project.name, update_modified=False
		)
		for row in artifact_rows(names):
			add_artifact(project.name, row.reference_doctype, row.reference_name)
