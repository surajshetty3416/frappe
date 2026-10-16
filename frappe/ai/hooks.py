# The /flow page: a Vite app (frontend/) built by `yarn build` into public/studio, its
# entry copied to www/flow/index.html. Every path under /flow serves that page.

doc_events = {
	"*": {
		"before_validate": "frappe.ai.artifacts.claim",
		"on_trash": ["frappe.ai.artifacts.claim", "frappe.ai.versions.delete"],
		"on_update": "frappe.ai.versions.record",
	}
}

# a session's tools run as its owner, so its content is theirs alone
has_permission = {
	"Flow Session": "frappe.ai.permissions.has_session_permission",
	"Flow Run": "frappe.ai.permissions.has_session_permission",
	"Flow Agent Memory": "frappe.ai.permissions.has_memory_permission",
}
permission_query_conditions = {
	"Flow Session": "frappe.ai.permissions.session_query_conditions",
	"Flow Run": "frappe.ai.permissions.session_query_conditions",
	"Flow Agent Memory": "frappe.ai.permissions.memory_query_conditions",
}

# Flow's references to other docs are bookkeeping — they must never block deleting
# the referenced doc. A knowledge chunk indexes a doc; a Flow Run records the doc an
# agent run acted on. The incremental sweep removes orphaned chunks afterwards.
# A session's Flow Model reference is historical bookkeeping and must not block deletion,
# nor its list of the artifacts it made; a deleted one drops out of that list when read.
ignore_links_on_delete = ["Flow Knowledge Chunk", "Flow Run", "Flow Session", "Flow Session Artifact"]

flow_agents = ["frappe.ai.orchestrator.agents"]

default_log_clearing_doctypes = {
	"Flow Session": 90,
}

scheduler_events = {
	"daily": [
		"frappe.ai.knowledge.ingest.sync_due_sources",
	],
	"cron": {
		"*/5 * * * *": [
			"frappe.ai.daemon.lifecycle.keep_alive",
		],
	},
}

flow_tools = [
	"frappe.ai.workspace.read_workspace",
	"frappe.ai.workspace.arrange_workspace",
	"frappe.ai.workspace.get_setup_state",
	"frappe.ai.workspace.configure_site",
	"frappe.ai.workspace.invite_people",
]

# the Spaces any organization can start with, and how a Space's conversation is filled (by an app)
space_templates = ["frappe.ai.setup_flow.default_templates"]

after_install = [
	"frappe.ai.shell.make_home_the_landing",
	"frappe.ai.permissions.ensure_assistant_role",
	"frappe.ai.lib.model.ensure_claude_code_model",
	"frappe.ai.assistant.sync_builtin_assistant",
	"frappe.ai.daemon.lifecycle.after_install",
]
after_migrate = [
	"frappe.ai.permissions.ensure_assistant_role",
	"frappe.ai.lib.model.ensure_claude_code_model",
	"frappe.ai.assistant.sync_builtin_assistant",
	"frappe.ai.lib.agent.sync_agents",
	"frappe.ai.lib.agent.sync_tools",
	"frappe.ai.daemon.lifecycle.after_migrate",
]
after_app_install = [
	"frappe.ai.assistant.sync_assistant_skills",
	"frappe.ai.lib.agent.sync_agents",
	"frappe.ai.lib.agent.sync_tools",
]
after_app_uninstall = ["frappe.ai.assistant.sync_assistant_skills"]
before_uninstall = ["frappe.ai.daemon.lifecycle.remove_site"]

extend_bootinfo = "frappe.ai.boot.boot_session"
