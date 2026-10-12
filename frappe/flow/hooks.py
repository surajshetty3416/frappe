

# The /flow page: a Vite app (frontend/) built by `yarn build` into public/frontend, its
# entry copied to www/flow/index.html. Every path under /flow serves that page.
add_to_apps_screen = [
	{
		"name": "flow",
		"logo": "/assets/frappe/frontend/flow.png",
		"title": "Flow",
		"route": "/flow",
		"has_permission": "frappe.flow.permissions.has_app_permission",
	}
]
website_route_rules = [
	{"from_route": "/flow/<path:app_path>", "to_route": "_frontend"},
	{"from_route": "/flow", "to_route": "_frontend"},
]

doc_events = {
	"*": {
		"after_insert": "frappe.flow.triggers.dispatch",
		"on_update": "frappe.flow.triggers.dispatch",
		"on_submit": "frappe.flow.triggers.dispatch",
		"on_cancel": "frappe.flow.triggers.dispatch",
		"on_trash": "frappe.flow.triggers.dispatch",
	}
}

# a session's tools run as its owner, so its content is theirs alone
has_permission = {
	"Flow Session": "frappe.flow.permissions.has_session_permission",
	"Flow Run": "frappe.flow.permissions.has_session_permission",
	"Flow Agent Memory": "frappe.flow.permissions.has_memory_permission",
}
permission_query_conditions = {
	"Flow Session": "frappe.flow.permissions.session_query_conditions",
	"Flow Run": "frappe.flow.permissions.session_query_conditions",
	"Flow Agent Memory": "frappe.flow.permissions.memory_query_conditions",
}

# Flow's references to other docs are bookkeeping — they must never block deleting
# the referenced doc. A knowledge chunk indexes a doc; a Flow Run records the doc a
# trigger acted on. The incremental sweep removes orphaned chunks afterwards.
# A session's Flow Model reference is historical bookkeeping and must not block deletion.
ignore_links_on_delete = ["Flow Knowledge Chunk", "Flow Run", "Flow Session"]

default_log_clearing_doctypes = {
	"Flow Session": 90,
}

scheduler_events = {
	"daily": [
		"frappe.flow.knowledge.ingest.sync_due_sources",
	],
	"cron": {
		"*/5 * * * *": [
			"frappe.flow.triggers.dispatch_scheduled",
			"frappe.flow.daemon.lifecycle.keep_alive",
		],
	},
}

after_install = [
	"frappe.flow.permissions.ensure_flow_role",
	"frappe.flow.assistant.sync_builtin_assistant",
	"frappe.flow.daemon.lifecycle.after_install",
]
after_migrate = [
	"frappe.flow.permissions.ensure_flow_role",
	"frappe.flow.assistant.sync_builtin_assistant",
	"frappe.flow.lib.agent.sync_agents",
	"frappe.flow.lib.agent.sync_tools",
	"frappe.flow.daemon.lifecycle.after_migrate",
]
after_app_install = ["frappe.flow.lib.agent.sync_agents", "frappe.flow.lib.agent.sync_tools"]
before_uninstall = ["frappe.flow.daemon.lifecycle.remove_site"]

extend_bootinfo = "frappe.flow.boot.boot_session"
