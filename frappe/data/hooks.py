studio_artifacts = {
	"DocType": {"label": "DocType", "route": "/studio/data/doctype/{name}", "title_field": "name"},
}

doc_events = {"DocType": {"before_save": "frappe.data.doctype.show_title_in_link"}}

flow_tools = ["frappe.data.flow_tools.generate_records"]

flow_skills = ["data/skills/data/SKILL.md"]
