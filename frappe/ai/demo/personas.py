"""The people the Frappeverse demo is shown as, each starting from their workspace at /home: a volunteer
at the check-in desk and a program lead reviewing proposals, whose workspaces are ready, and a new
sponsor manager and the site's admin, who set theirs up with the assistant on first sign-in. They get
the demo project's artifacts through shares, as a team would hand them out."""

import json
from typing import Any

import frappe
from frappe.ai.home import viewable
from frappe.ai.permissions import ASSISTANT_USER_ROLE
from frappe.ai.workspace import SETUP_CHAT_KEY, SETUP_KEY, SITE_SETUP_KEY, WORKSPACE_KEY, clean
from frappe.analytics.permissions import workbook_of
from frappe.desk.form.assign_to import add as assign
from frappe.desk.like import _toggle_like
from frappe.share import add_docshare
from frappe.utils.password import update_password

REVIEW_WORKFLOW = "Talk Proposal Review"
# (from, action, to), each for the Program Committee
REVIEW_TRANSITIONS = [
	("Submitted", "Start Review", "Under Review"),
	("Under Review", "Shortlist", "Shortlisted"),
	("Under Review", "Reject", "Rejected"),
	("Shortlisted", "Accept", "Accepted"),
	("Shortlisted", "Reject", "Rejected"),
]
REVIEW_STATES = ["Submitted", "Under Review", "Shortlisted", "Accepted", "Rejected", "Withdrawn"]

CHECK_IN_SCRIPT = "Frappeverse Check In Marks Attendee"

PERSONAS = [
	{
		"email": "neha@example.com",
		"first_name": "Neha",
		"last_name": "Kulkarni",
		"persona": "Volunteer at the check-in desk: checks people in from her workspace",
		"roles": [ASSISTANT_USER_ROLE, "Analytics User", "Volunteer"],
		"write": [],
		"pin": ["Insights Dashboard v3"],
		"workspace": [
			{
				"type": "queue",
				"title": "Check people in",
				"size": "l",
				"doctype": "Attendee",
				"filters": {"payment_status": "Paid", "checked_in": 0},
				"fields": ["ticket_code", "ticket_type", "company"],
				"order_by": "full_name asc",
				"search": True,
				"search_fields": ["ticket_code", "email", "company"],
				"actions": [
					{
						"label": "Check in",
						"kind": "create",
						"doctype": "Check In",
						"values": {"attendee": "{name}", "day": "Day 1", "kind": "Arrival", "gate": "Gate 1"},
					}
				],
			},
			{"type": "inbox", "title": "My tasks", "size": "s"},
			{
				"type": "quick_entry",
				"title": "Re-entry",
				"size": "s",
				"doctype": "Check In",
				"fields": ["attendee", "gate"],
				"defaults": {"day": "Day 1", "kind": "Re-entry"},
			},
			{"type": "chart", "chart": "Attendees by Ticket Type", "size": "s"},
		],
		"todos": [
			{"description": "Cover the Help Desk from 2 to 4 pm on Day 1, while Priya is on her break."},
		],
	},
	{
		"email": "rahul@example.com",
		"first_name": "Rahul",
		"last_name": "Menon",
		"persona": "Program lead: reviews proposals and watches registrations from his workspace",
		"roles": [ASSISTANT_USER_ROLE, "Analytics User", "Program Committee", "Volunteer"],
		"write": ["Insights Dashboard v3"],
		"pin": ["Insights Dashboard v3", "Studio App"],
		"workspace": [
			{"type": "inbox", "title": "Proposals and tasks waiting on me", "size": "l"},
			{"type": "chart", "chart": "Paid Registrations", "size": "s"},
			{
				"type": "queue",
				"title": "Sessions filling up",
				"size": "s",
				"doctype": "Session",
				"filters": {"status": "Scheduled"},
				"fields": ["room", "day", "registered_count", "capacity"],
				"order_by": "registered_count desc",
			},
			{"type": "chart", "chart": "Proposals by Status", "size": "s"},
			{"type": "chart", "chart": "Registrations per Week", "size": "l"},
			{"type": "chart", "chart": "Ticket Revenue", "size": "s"},
		],
		"assign": {"doctype": "Talk Proposal", "status": "Under Review", "count": 3},
	},
	{
		"email": "meera@example.com",
		"first_name": "Meera",
		"last_name": "Iyer",
		"persona": "New sponsor manager: sets up her workspace with the assistant on first sign-in",
		"roles": [ASSISTANT_USER_ROLE, "Analytics User", "Sponsor Manager"],
		"write": [],
		"pin": [],
	},
	{
		"email": "arjun@example.com",
		"first_name": "Arjun",
		"last_name": "Shah",
		"persona": "Admin: sets up the site, the team and his workspace with the assistant",
		"roles": [
			ASSISTANT_USER_ROLE,
			"System Manager",
			"Website Manager",
			"App Manager",
			"Analytics Manager",
		],
		"write": None,
		"pin": ["Builder Page"],
	},
]


def setup_personas(artifacts: list[dict[str, Any]]) -> list[dict[str, str]]:
	"""Each persona as a user with a new password, sharing and pinning the demo's `artifacts`, with
	the review workflow and check-in rule their work runs on; their logins, for whoever shows the demo."""
	setup_review_workflow()
	setup_check_in_rule()
	frappe.defaults.clear_default(SITE_SETUP_KEY, parent="__default")
	logins = []
	for persona in PERSONAS:
		user = ensure_user(persona)
		for artifact in artifacts:
			doctype, name = artifact["doctype"], artifact["name"]
			if persona["write"] is not None:
				share(doctype, name, user, write=doctype in persona["write"])
			if doctype in persona["pin"] and artifact is first_of(artifacts, doctype):
				_toggle_like(doctype, name, "Yes", user=user)
		set_workspace(user, persona.get("workspace"))
		for todo in persona.get("todos") or []:
			if not frappe.db.exists("ToDo", {"allocated_to": user, "description": todo["description"]}):
				frappe.get_doc({"doctype": "ToDo", "allocated_to": user, **todo}).insert(
					ignore_permissions=True
				)
		if persona.get("assign"):
			assign_proposals(user, **persona["assign"])
		password = frappe.generate_hash(length=12)
		update_password(user, password)
		logins.append({"user": user, "password": password, "persona": persona["persona"]})
	frappe.db.commit()
	return logins


def set_workspace(user: str, widgets: list[dict[str, Any]] | None) -> None:
	"""The persona's ready workspace, or none, so they set it up on first sign-in. A chart widget
	names its chart by title here."""
	frappe.defaults.clear_default(WORKSPACE_KEY, parent=user)
	frappe.defaults.clear_default(SETUP_KEY, parent=user)
	frappe.defaults.clear_default(SETUP_CHAT_KEY, parent=user)
	if not widgets:
		return
	widgets = [dict(widget) for widget in widgets]
	for widget in widgets:
		if widget["type"] == "chart":
			widget["chart"] = frappe.db.get_value("Insights Chart v3", {"title": widget["chart"]})
	widgets = [widget for widget in widgets if widget["type"] != "chart" or widget["chart"]]
	frappe.defaults.set_user_default(WORKSPACE_KEY, json.dumps(clean(widgets)), user)
	frappe.defaults.set_user_default(SETUP_KEY, "1", user)


def setup_review_workflow() -> None:
	"""The Program Committee reviews proposals through a workflow on their status, so what waits on
	a reviewer shows as an approval; the open proposals get theirs."""
	from frappe.workflow.doctype.workflow_action.workflow_action import process_workflow_actions

	for state in REVIEW_STATES:
		if not frappe.db.exists("Workflow State", state):
			frappe.get_doc({"doctype": "Workflow State", "workflow_state_name": state}).insert()
	for _from, action, _to in REVIEW_TRANSITIONS:
		if not frappe.db.exists("Workflow Action Master", action):
			frappe.get_doc({"doctype": "Workflow Action Master", "workflow_action_name": action}).insert()
	if not frappe.db.exists("Workflow", REVIEW_WORKFLOW):
		frappe.get_doc(
			{
				"doctype": "Workflow",
				"workflow_name": REVIEW_WORKFLOW,
				"document_type": "Talk Proposal",
				"workflow_state_field": "status",
				"is_active": 1,
				"send_email_alert": 0,
				"states": [
					{"state": state, "doc_status": "0", "allow_edit": "Program Committee"}
					for state in REVIEW_STATES
				],
				"transitions": [
					{
						"state": state,
						"action": action,
						"next_state": next_state,
						"allowed": "Program Committee",
					}
					for state, action, next_state in REVIEW_TRANSITIONS
				],
			}
		).insert()
	for name in frappe.get_all(
		"Talk Proposal",
		filters={"status": ("in", ("Submitted", "Under Review", "Shortlisted"))},
		pluck="name",
	):
		process_workflow_actions(frappe.get_doc("Talk Proposal", name), "on_update")


def setup_check_in_rule() -> None:
	"""A check-in marks its attendee as in, so the check-in queue drops them."""
	if frappe.db.exists("Server Script", CHECK_IN_SCRIPT):
		return
	frappe.get_doc(
		{
			"doctype": "Server Script",
			"name": CHECK_IN_SCRIPT,
			"script_type": "DocType Event",
			"reference_doctype": "Check In",
			"doctype_event": "After Insert",
			"script": 'frappe.db.set_value("Attendee", doc.attendee, "checked_in", 1)',
		}
	).insert()


def assign_proposals(user: str, doctype: str, status: str, count: int) -> None:
	for name in frappe.get_all(
		doctype, filters={"status": status}, pluck="name", order_by="name", limit=count
	):
		if not frappe.db.exists(
			"ToDo",
			{"allocated_to": user, "reference_type": doctype, "reference_name": name, "status": "Open"},
		):
			assign(
				{"doctype": doctype, "name": name, "assign_to": [user], "description": "Review this proposal"}
			)


def share(doctype: str, name: str, user: str, write: bool) -> None:
	"""Share the artifact with `user`; a dashboard is changed through its workbook, so that is what
	a writer gets."""
	flags = {"ignore_share_permission": True}
	if write and doctype == "Insights Dashboard v3":
		workbook = workbook_of(frappe.get_doc(doctype, name))
		add_docshare("Insights Workbook", workbook, user, read=1, write=1, flags=flags)
		write = False
	add_docshare(doctype, name, user, read=1, write=int(write), flags=flags)


def ensure_user(persona: dict[str, Any]) -> str:
	if not frappe.db.exists("User", persona["email"]):
		frappe.get_doc(
			{
				"doctype": "User",
				"email": persona["email"],
				"first_name": persona["first_name"],
				"last_name": persona["last_name"],
				"send_welcome_email": 0,
			}
		).insert(ignore_permissions=True)
	frappe.get_doc("User", persona["email"]).add_roles(*persona["roles"])
	return persona["email"]


def first_of(artifacts: list[dict[str, Any]], doctype: str) -> dict[str, Any] | None:
	return next((artifact for artifact in artifacts if artifact["doctype"] == doctype), None)


def demo_artifacts(project: str) -> list[dict[str, Any]]:
	"""What the demo project's chats made that the home can open."""
	types = viewable()
	return [
		{"doctype": row.reference_doctype, "name": row.reference_name}
		for row in frappe.get_doc("Studio Project", project).artifacts
		if row.reference_doctype in types and frappe.db.exists(row.reference_doctype, row.reference_name)
	]
