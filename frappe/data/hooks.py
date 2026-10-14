studio_artifacts = {
	"DocType": {"label": "DocType", "route": "/studio/data/doctype/{name}", "title_field": "name"},
}

doc_events = {
	"DocType": {
		"before_save": "frappe.data.doctype.show_title_in_link",
		"before_flow_save": "frappe.data.doctype.grant_named_rights",
		"after_flow_save": "frappe.data.doctype.describe_rights",
	}
}

flow_tools = ["frappe.data.flow_tools.generate_records"]
