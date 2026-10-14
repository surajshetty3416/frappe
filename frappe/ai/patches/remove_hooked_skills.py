import frappe


# Skills from the removed `flow_skills` hook have title-case names and no app. On MariaDB, sync_skills
# would update one as its lowercase skills/ folder, then delete it as not shipped.
def execute():
	names = frappe.get_all("Flow Skill", {"is_system_generated": 1, "app": ("is", "not set")}, pluck="name")
	if not names:
		return
	frappe.db.delete("Flow Agent Skill", {"skill": ("in", names)})
	frappe.db.delete("Flow Skill", {"name": ("in", names)})
