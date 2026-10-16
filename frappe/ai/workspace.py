# Copyright (c) 2026, Frappe Technologies and contributors
# License: MIT. See LICENSE

"""The workspace: one view where a person does most of their work. It holds widgets, not links: a
queue of records with buttons that act on them, the approvals and assignments waiting on the person,
a chart, a short form that creates a record, an app shown in place, a note.

Each person's workspace is theirs. The assistant builds it in their first-run setup and changes it
when they ask; they can also move, resize and remove widgets by hand. Until they have one, they get
the one a System Manager saved for everyone, or DEFAULT_WORKSPACE.

A widget's actions run as the person, through the same permission checks as any other write."""

from __future__ import annotations

import json
import re
from typing import Annotated, Any

import frappe
from frappe import _
from frappe.ai.home import get_view, viewable
from frappe.ai.lib.tool import ToolContext, tool
from frappe.ai.permissions import ASSISTANT_USER_ROLE
from frappe.model import data_fieldtypes, table_fields
from frappe.utils import get_fullname, nowdate, strip_html

WORKSPACE_KEY = "studio_workspace"
SETUP_KEY = "studio_setup_done"
SETUP_CHAT_KEY = "studio_setup_chat"
WELCOMED_KEY = "studio_welcomed"
SITE_SETUP_KEY = "studio_site_setup_done"
ORGANIZATION_KEY = "studio_organization"

QUEUE_LIMIT = 20
# the fields every DocType has, which a queue may show though its meta does not list them
STANDARD_FIELDS = {
	"name": {"label": "ID", "fieldtype": "Data"},
	"owner": {"label": "Created By", "fieldtype": "Data"},
	"creation": {"label": "Created", "fieldtype": "Datetime"},
	"modified": {"label": "Updated", "fieldtype": "Datetime"},
}
INBOX_LIMIT = 30
DONE_LIMIT = 10
# a record's long text and a comment, as much of each as a task card shows
TEXT_LIMIT = 800
NOTE_LIMIT = 300
LONG_TEXT = ("Text Editor", "Text", "Small Text", "Long Text", "Markdown Editor", "HTML Editor")
# the fields that name who a record comes from, before its owner
REQUESTER_FIELDS = ("raised_by", "requested_by", "requester")
COUNT_LIMIT = 1000
# a third, two thirds or the whole row, so widgets always pack; a half (m) is read as a third
SIZES = ("s", "l", "xl")

# what each widget does, and the keys it takes besides `type`, `title` and `size`
WIDGETS = {
	"queue": (
		"Records of one DocType that wait on the person, newest or most urgent first, each with buttons "
		"that act on it in place. `filters` are frappe filters ({field: value} or {field: [op, value]}; "
		"'@me' is the person, '@today' is today). `fields` are up to four fields shown on each row. "
		"`order_by` is 'field asc|desc'. `search` adds a search box over the title and `search_fields`. "
		"`actions` are buttons on each row: {label, kind: 'set', field, value} changes a field; "
		"{label, kind: 'workflow', action} applies a workflow action; {label, kind: 'assign'} assigns the "
		"record to the person; {label, kind: 'create', doctype, "
		"values} creates a record from the row, where '{name}' or '{field}' in a value is the row's. "
		"An action with `when: {field: value}` shows only on rows that match. An action that needs more "
		"than a click asks for it before it runs: `fields` are the record's fields to fill in, `reply` "
		"is the field holding the email address to reply to first, and `comment` ('optional' or "
		"'required') is a note added to the record, such as a reason to decline.",
		("doctype",),
		("filters", "fields", "order_by", "search", "search_fields", "actions", "limit"),
	),
	"inbox": (
		"The person's open assignments and the approvals waiting on their roles, across DocTypes, "
		"each with its workflow actions",
		(),
		(),
	),
	"chart": (
		"A saved analytics chart or number card (an Insights Chart v3, by name), live",
		("chart",),
		(),
	),
	"quick_entry": (
		"A short form that creates a record of `doctype` with `fields`, and `defaults` for the rest",
		("doctype", "fields"),
		("defaults",),
	),
	"embed": (
		"An app, web page or dashboard (`doctype` and `name` of a Studio artifact), used in place",
		("doctype", "name"),
		(),
	),
	"note": ("Text the person keeps in view: a plan, a checklist, a reminder", ("text",), ()),
	"number_card": ("A desk Number Card, by name, as a tile", ("number_card",), ()),
	"dashboard_chart": ("A desk Dashboard Chart, by name", ("dashboard_chart",), ()),
}

DEFAULT_WORKSPACE = [{"id": "inbox", "type": "inbox", "size": "l"}]


@frappe.whitelist()
def get_workspace() -> dict[str, Any]:
	"""The user's widgets, and what the user still has to set up."""
	from frappe.ai.spaces import home_slices

	user = frappe.session.user
	return {
		"widgets": with_charts(one_inbox(workspace(personal_default=[]) + home_slices())),
		"customized": bool(frappe.defaults.get_defaults_for(user).get(WORKSPACE_KEY)),
		"setup": setup_state(),
		"organization": (organization() or {}).get("name"),
		"can_set_default": "System Manager" in frappe.get_roles(),
	}


@frappe.whitelist(methods=["POST"])
def save_workspace(widgets: list[dict[str, Any]] | str, for_everyone: bool = False) -> list[dict[str, Any]]:
	"""Keep `widgets` as the user's workspace, or, for a System Manager, as everyone's who has not
	arranged their own."""
	widgets = clean(frappe.parse_json(widgets))
	value = json.dumps(widgets)
	if frappe.utils.sbool(for_everyone):
		frappe.only_for("System Manager")
		frappe.defaults.set_global_default(WORKSPACE_KEY, value)
	else:
		frappe.defaults.set_user_default(WORKSPACE_KEY, value)
	frappe.publish_realtime("studio_workspace", user=frappe.session.user, after_commit=True)
	return widgets


@frappe.whitelist(methods=["POST"])
def reset_workspace() -> None:
	"""Give the user the workspace everyone gets again."""
	frappe.defaults.clear_user_default(WORKSPACE_KEY)
	frappe.publish_realtime("studio_workspace", user=frappe.session.user, after_commit=True)


@frappe.whitelist()
def get_widget(widget: str, txt: str | None = None, space: str | None = None) -> dict[str, Any]:
	"""What one of the user's widgets, or of `space`'s, shows now."""
	spec = find_widget(widget, space)
	kind = spec["type"]
	if kind == "queue":
		return queue_rows(spec, txt)
	if kind == "inbox":
		return {"items": inbox(skip=queued_assignments() if not space else ()), "done": inbox_done()}
	if kind == "quick_entry":
		return {"fields": form_fields(spec["doctype"], spec["fields"]), "can_create": can("create", spec)}
	if kind == "embed":
		return {"view": get_view(spec["doctype"], spec["name"]) if readable(spec) else None}
	if kind == "number_card":
		return number_card(spec["number_card"])
	if kind == "dashboard_chart":
		return dashboard_chart(spec["dashboard_chart"])
	return {}


@frappe.whitelist(methods=["POST"])
def act(
	widget: str,
	action: int,
	name: str,
	space: str | None = None,
	values: dict[str, Any] | str | None = None,
	comment: str | None = None,
	reply: str | None = None,
) -> dict[str, Any]:
	"""Run a queue widget's `action` on the record `name`: send the `reply` it asks for, save the
	`values` of its fields, make its change, and add the `comment`. Says what it did."""
	spec = find_widget(widget, space)
	if spec["type"] != "queue":
		frappe.throw(_("Only a queue widget acts on its records."))
	try:
		button = spec["actions"][int(action)]
	except (IndexError, TypeError, ValueError):
		frappe.throw(_("This widget has no such action."))
	doc = frappe.get_doc(spec["doctype"], name)
	comment, reply = (comment or "").strip(), (reply or "").strip()
	if button.get("comment") == "required" and not comment:
		frappe.throw(_("Say why, to {0}.").format(button["label"]), title=_("Note Needed"))
	if button.get("reply"):
		if not reply:
			frappe.throw(_("Write the reply first."), title=_("Reply Needed"))
		send_reply(doc, button["reply"], reply)
		doc.reload()
	# each save is kept as a Version, even under tests: the day's done is read back from them
	given = frappe.parse_json(values) or {}
	filled = {field: given.get(field) for field in button.get("fields") or [] if field in given}
	if filled:
		doc.check_permission("write")
		doc.update(filled)
	if button["kind"] == "set":
		doc.check_permission("write")
		doc.set(button["field"], resolve(button["value"]))
		doc.save(ignore_version=False)
	elif button["kind"] == "assign":
		from frappe.desk.form.assign_to import add

		doc.check_permission("read")
		if filled:
			doc.save(ignore_version=False)
		add({"doctype": doc.doctype, "name": doc.name, "assign_to": [frappe.session.user]})
	elif button["kind"] == "workflow":
		from frappe.model.workflow import apply_workflow

		doc.check_permission("read")
		if filled:
			doc.save(ignore_version=False)
		apply_workflow(doc, button["action"])
	else:
		made = {field: fill(value, doc) for field, value in (button.get("values") or {}).items()}
		doc = frappe.get_doc({"doctype": button["doctype"], **made}).insert()
	if comment:
		doc.add_comment("Comment", comment)
	return {
		"doctype": doc.doctype,
		"name": doc.name,
		"did": steps(button, frappe.get_meta(spec["doctype"])),
		"undo": button["kind"] in ("set", "assign"),
	}


@frappe.whitelist(methods=["POST"])
def undo(widget: str, name: str, space: str | None = None) -> None:
	"""Take back what the user did today to the record `name` from a queue: the fields of their
	last change, or taking it. A workflow state, and an email sent, stay as they are."""
	from frappe.desk.form.assign_to import remove

	spec = find_widget(widget, space)
	if spec["type"] != "queue":
		frappe.throw(_("Only a queue widget acts on its records."))
	doc = frappe.get_doc(spec["doctype"], name)
	changed = undoable(doc.doctype, name)
	if changed:
		doc.check_permission("write")
		for field, old, _new in changed:
			doc.set(field, old)
		doc.save()
		return
	if not taken_today(doc.doctype, [name]):
		frappe.throw(_("There is nothing of yours to undo on {0} today.").format(title_of(doc)))
	remove(doc.doctype, name, frappe.session.user)


@frappe.whitelist(methods=["POST"])
def create(widget: str, values: dict[str, Any] | str, space: str | None = None) -> dict[str, Any]:
	"""Create a record from a quick entry widget: its fields from `values`, the rest from its defaults."""
	spec = find_widget(widget, space)
	if spec["type"] != "quick_entry":
		frappe.throw(_("Only a quick entry widget creates records."))
	values = frappe.parse_json(values)
	given = {field: values.get(field) for field in spec["fields"] if values.get(field) not in (None, "")}
	defaults = {field: resolve(value) for field, value in (spec.get("defaults") or {}).items()}
	doc = frappe.get_doc({"doctype": spec["doctype"], **defaults, **given}).insert()
	return {"doctype": doc.doctype, "name": doc.name, "title": title_of(doc)}


@frappe.whitelist()
def get_inbox() -> dict[str, Any]:
	"""What waits on the user: their assignments, the approvals for their roles, and @mentions;
	and what they finished today."""
	return {"items": inbox(), "done": inbox_done()}


@frappe.whitelist(methods=["POST"])
def respond(kind: str, name: str, action: str | None = None, comment: str | None = None) -> None:
	"""Act on an inbox item: close an assignment, mark a mention read, or apply a workflow action
	to the record an approval waits on; with `comment`, add it to the record as a note."""
	comment = (comment or "").strip()
	if kind == "mention":
		from frappe.desk.doctype.notification_log.notification_log import mark_as_read

		mark_as_read(name)
		return
	if kind == "assignment":
		todo = own_todo(name)
		todo.status = "Closed"
		todo.save(ignore_permissions=True)
		if comment and todo.reference_type and todo.reference_name:
			frappe.get_doc(todo.reference_type, todo.reference_name).add_comment("Comment", comment)
		return
	from frappe.model.workflow import apply_workflow

	pending = frappe.get_doc("Workflow Action", name)
	pending.check_permission("read")
	if needs_reason(action) and not comment:
		frappe.throw(_("Say why, to {0}.").format(action), title=_("Note Needed"))
	doc = apply_workflow(frappe.get_doc(pending.reference_doctype, pending.reference_name), action)
	if comment:
		doc.add_comment("Comment", comment)


@frappe.whitelist(methods=["POST"])
def reopen(name: str) -> None:
	"""Open again an assignment the user marked done."""
	todo = own_todo(name)
	todo.status = "Open"
	todo.save(ignore_permissions=True)


@frappe.whitelist()
def get_record(doctype: str, name: str) -> dict[str, Any]:
	"""A record as the workspace's pane shows it: its fields, their values, and its workflow actions."""
	from frappe.model.workflow import get_transitions

	doc = frappe.get_doc(doctype, name)
	doc.check_permission("read")
	meta = frappe.get_meta(doctype)
	can_write = bool(doc.has_permission("write"))
	fields = [
		{**field, "read_only": field["read_only"] or not can_write}
		for field in form_fields(doctype, [df.fieldname for df in meta.fields])
		if not frappe.get_meta(doctype).get_field(field["fieldname"]).hidden
	]
	try:
		transitions = list(dict.fromkeys(t.action for t in get_transitions(doc)))
	except frappe.ValidationError:
		transitions = []
	return {
		"doctype": doctype,
		"name": name,
		"title": title_of(doc),
		"url": doc.get_url(),
		"fields": fields,
		"values": {field["fieldname"]: doc.get(field["fieldname"]) for field in fields},
		"can_write": can_write,
		"transitions": transitions,
		"modified": doc.modified,
	}


@frappe.whitelist()
def get_task(doctype: str, name: str) -> dict[str, Any]:
	"""A record as a task card shows it: who it is from, what is at stake, what it says, and the
	latest comments and emails on it."""
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("read")
	return {
		"title": title_of(doc),
		"url": doc.get_url(),
		"who": requester(doc),
		"created": doc.creation,
		"facts": facts(doc),
		"text": long_text(doc),
		"timeline": timeline(doc),
	}


@frappe.whitelist(methods=["POST"])
def apply_transition(doctype: str, name: str, action: str) -> None:
	"""Apply a workflow action to a record open in the pane."""
	from frappe.model.workflow import apply_workflow

	apply_workflow(frappe.get_doc(doctype, name), action)


@frappe.whitelist(methods=["POST"])
def keep_setup_chat(session: str) -> None:
	"""The user's setup conversation, which their setup picks up again on any device."""
	frappe.get_doc("Flow Session", session).check_permission("write")
	frappe.defaults.set_user_default(SETUP_CHAT_KEY, session)


@frappe.whitelist(methods=["POST"])
def dismiss_welcome() -> None:
	frappe.defaults.set_user_default(WELCOMED_KEY, "1")


@frappe.whitelist(methods=["POST"])
def finish_setup() -> None:
	"""The admin is done setting the site up, or skips the rest of it."""
	frappe.only_for("System Manager")
	frappe.defaults.set_global_default(SITE_SETUP_KEY, "1")


@tool
def read_workspace(*, ctx: ToolContext) -> dict[str, Any]:
	"""The person's workspace (/home): their widgets in order, and every widget type with the keys
	it takes. Read it before you change it."""
	return {
		"widgets": workspace(),
		"widget_types": {
			kind: {"does": does, "needs": needs, "may_have": extra}
			for kind, (does, needs, extra) in WIDGETS.items()
		},
		"sizes": "s is a third of the row, l two thirds, xl the whole row",
	}


@tool
def arrange_workspace(
	widgets: Annotated[
		list[dict[str, Any]],
		"Every widget of the workspace, most urgent first, each {type, title, size, ...the keys its "
		"type takes}; keep the `id` of a widget that stays",
	],
	*,
	ctx: ToolContext,
) -> list[dict[str, Any]]:
	"""Set the person's workspace (/home): add, change, resize, reorder or remove widgets. Send the
	whole list. The workspace on their screen updates at once."""
	return save_workspace(widgets)


@tool
def get_setup_state(*, ctx: ToolContext) -> dict[str, Any]:
	"""Where the person's first-run setup stands: who they are, the organization, and, for a System
	Manager setting up the site, its settings, roles and people."""
	user = frappe.get_doc("User", frappe.session.user)
	state = {
		"person": {"email": user.name, "full_name": user.full_name, "roles": frappe.get_roles()},
		"organization": organization(),
		**setup_state(),
	}
	if state["site"]:
		settings = frappe.get_single("System Settings")
		state["site_settings"] = {
			key: settings.get(key) for key in ("country", "currency", "time_zone", "language")
		}
		state["roles"] = frappe.get_all(
			"Role", filters={"disabled": 0, "is_custom": 1}, pluck="name"
		) + frappe.get_all("Role", filters={"disabled": 0, "is_custom": 0, "desk_access": 1}, pluck="name")
		state["people"] = frappe.get_all(
			"User",
			filters={
				"user_type": "System User",
				"enabled": 1,
				"name": ("not in", ("Administrator", "Guest")),
			},
			fields=["name", "full_name"],
		)
	return state


@tool(requires_confirmation=True)
def configure_site(
	organization: Annotated[str, "The organization's name"],
	about: Annotated[str, "What the organization does, in a sentence or two, as the person put it"],
	country: Annotated[str, "Country, as named in the Country DocType"],
	currency: Annotated[str, "Currency code, such as INR"],
	time_zone: Annotated[str, "IANA time zone, such as Asia/Kolkata"],
	language: Annotated[str, "Language code, such as en"] = "en",
	*,
	ctx: ToolContext,
) -> dict[str, Any]:
	"""Set the site up for the organization: its name and what it does, its country, currency, time
	zone and language. Only a System Manager, once, in the first-run setup."""
	from frappe.ai.setup_flow import save_organization

	save_organization(organization, about, country, currency, time_zone, language)
	return {"organization": organization, "country": country, "currency": currency, "time_zone": time_zone}


@tool(requires_confirmation=True)
def invite_people(
	people: Annotated[
		list[dict[str, Any]],
		"Each {email, first_name, last_name?, roles: [role names]}; roles from get_setup_state",
	],
	*,
	ctx: ToolContext,
) -> list[dict[str, Any]]:
	"""Invite people to the site with the roles their work needs. Each gets a welcome email, and sets
	up their own workspace when they first sign in. Only a System Manager."""
	from frappe.ai.setup_flow import invite_person

	frappe.only_for("System Manager")
	invited = [
		invite_person(person["email"].strip().lower(), person.get("first_name"), person.get("roles") or [])
		for person in people
	]
	return invited


def setup_state() -> dict[str, Any]:
	"""Only an admin sets up, and only the site; everyone else's Home is ready when they arrive,
	with a welcome until they put it away."""
	site = "System Manager" in frappe.get_roles() and not frappe.defaults.get_global_default(SITE_SETUP_KEY)
	return {
		"needed": site,
		"site": site,
		"chat": frappe.defaults.get_user_default(SETUP_CHAT_KEY),
		"welcome": not frappe.defaults.get_user_default(WELCOMED_KEY),
	}


def organization() -> dict[str, str] | None:
	saved = frappe.defaults.get_global_default(ORGANIZATION_KEY)
	return json.loads(saved) if saved else None


def workspace(personal_default: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
	saved = frappe.defaults.get_user_default(WORKSPACE_KEY)
	if saved:
		return json.loads(saved)
	return clean(DEFAULT_WORKSPACE if personal_default is None else personal_default)


def one_inbox(widgets: list[dict[str, Any]]) -> list[dict[str, Any]]:
	"""A Home has one inbox, its own, on top: everything that waits on the person, less what its
	queues show. A Space's inbox is that Space's, and stays on the Space."""
	own = next((widget for widget in widgets if widget["type"] == "inbox" and not widget.get("space")), None)
	rest = [widget for widget in widgets if widget["type"] != "inbox"]
	return [own or clean(DEFAULT_WORKSPACE)[0], *rest]


def find_widget(widget: str, space: str | None = None) -> dict[str, Any]:
	from frappe.ai.spaces import permitted, space_widgets

	widgets = space_widgets(permitted(space)) if space else [*workspace(), *clean(DEFAULT_WORKSPACE)]
	found = next((spec for spec in widgets if spec["id"] == widget), None)
	if not found:
		frappe.throw(_("This widget is no longer on your workspace."))
	return found


def with_charts(widgets: list[dict[str, Any]]) -> list[dict[str, Any]]:
	"""Widgets with each chart's type and title, so a page sets numbers apart from charts and names
	a chart its reader may view but not open."""
	charts = [widget["chart"] for widget in widgets if widget["type"] == "chart"]
	found = {
		chart.name: chart
		for chart in frappe.get_all(
			"Insights Chart v3",
			filters={"name": ("in", charts or [""])},
			fields=["name", "chart_type", "title"],
		)
	}
	labelled = []
	for widget in widgets:
		if widget["type"] == "chart":
			chart = found.get(widget["chart"]) or {}
			widget = {**widget, "chart_type": chart.get("chart_type"), "chart_title": chart.get("title")}
		labelled.append(widget)
	return labelled


def clean(widgets: list[dict[str, Any]]) -> list[dict[str, Any]]:
	"""Widgets as the workspace keeps them: known types with the keys they take, each with an id,
	and fields and actions that exist on their DocType."""
	cleaned = []
	for widget in widgets:
		kind = widget.get("type")
		if kind not in WIDGETS:
			frappe.throw(
				_("The workspace has no widget of type {0}.").format(kind), title=_("Invalid Widget")
			)
		_does, needs, extra = WIDGETS[kind]
		row = {
			"id": widget.get("id") or frappe.generate_hash(length=8),
			"type": kind,
			"title": widget.get("title") or None,
			"size": widget.get("size") if widget.get("size") in SIZES else "s",
		}
		for key in needs:
			if widget.get(key) in (None, "", []):
				frappe.throw(_("A {0} widget needs {1}.").format(kind, key), title=_("Invalid Widget"))
			row[key] = widget[key]
		for key in extra:
			if widget.get(key) not in (None, "", [], {}):
				row[key] = widget[key]
		# a Space's widget for its members' Homes
		if widget.get("home"):
			row["home"] = 1
		check(row)
		cleaned.append(row)
	return cleaned


def check(widget: dict[str, Any]) -> None:
	kind = widget["type"]
	if kind == "chart" and not frappe.db.exists("Insights Chart v3", widget["chart"]):
		frappe.throw(_("No chart named {0}.").format(widget["chart"]), title=_("Invalid Widget"))
	for doctype, key in (("Number Card", "number_card"), ("Dashboard Chart", "dashboard_chart")):
		if kind == key and not frappe.db.exists(doctype, widget[key]):
			frappe.throw(_("No {0} named {1}.").format(_(doctype), widget[key]), title=_("Invalid Widget"))
	if kind == "embed" and widget["doctype"] not in viewable():
		frappe.throw(
			_("{0} cannot be shown in the workspace.").format(widget["doctype"]), title=_("Invalid Widget")
		)
	if kind not in ("queue", "quick_entry"):
		return
	meta = frappe.get_meta(widget["doctype"])
	for field in widget.get("fields") or []:
		if not meta.get_field(field) and field not in STANDARD_FIELDS:
			frappe.throw(
				_("{0} has no field {1}.").format(widget["doctype"], field), title=_("Invalid Widget")
			)
	for action in widget.get("actions") or []:
		for field in [*(action.get("fields") or []), *([action["reply"]] if action.get("reply") else [])]:
			if not meta.get_field(field):
				frappe.throw(
					_("{0} has no field {1}.").format(widget["doctype"], field), title=_("Invalid Widget")
				)
		if action.get("comment") not in (None, "optional", "required"):
			frappe.throw(_("An action's comment is optional or required."), title=_("Invalid Widget"))
		if action.get("kind") == "set":
			df = meta.get_field(action.get("field") or "")
			if not df:
				frappe.throw(
					_("{0} has no field {1}.").format(widget["doctype"], action.get("field")),
					title=_("Invalid Widget"),
				)
			if df.fieldtype == "Select" and str(action.get("value")) not in (df.options or "").split("\n"):
				frappe.throw(
					_("{0} is not an option of {1}.").format(action.get("value"), df.label),
					title=_("Invalid Widget"),
				)
		elif action.get("kind") == "create":
			if not action.get("doctype") or not frappe.db.exists("DocType", action["doctype"]):
				frappe.throw(_("A create action needs a DocType."), title=_("Invalid Widget"))
		elif action.get("kind") == "assign":
			pass
		elif action.get("kind") != "workflow" or not action.get("action"):
			frappe.throw(_("An action is set, assign, workflow or create."), title=_("Invalid Widget"))
		if not action.get("label"):
			frappe.throw(_("An action needs a label."), title=_("Invalid Widget"))


def queue_rows(spec: dict[str, Any], txt: str | None) -> dict[str, Any]:
	doctype = spec["doctype"]
	if not frappe.has_permission(doctype, "read"):
		return {"rows": [], "count": 0, "fields": [], "denied": True}
	meta = frappe.get_meta(doctype)
	shown = [field for field in spec.get("fields") or [] if field != "name"]
	when = {field for action in spec.get("actions") or [] for field in (action.get("when") or {})}
	replies = {action["reply"] for action in spec.get("actions") or [] if action.get("reply")}
	columns = list(
		dict.fromkeys(["name", *([meta.title_field] if meta.title_field else []), *shown, *when, *replies])
	)
	filters = resolve(spec.get("filters") or {})
	or_filters = None
	if txt:
		searched = [meta.title_field or "name", *(spec.get("search_fields") or [])]
		or_filters = [[doctype, field, "like", f"%{txt}%"] for field in dict.fromkeys(["name", *searched])]
	limit = min(int(spec.get("limit") or QUEUE_LIMIT), QUEUE_LIMIT)
	rows = frappe.get_list(
		doctype,
		filters=filters,
		or_filters=or_filters,
		fields=columns,
		order_by=order_by(spec.get("order_by"), meta),
		limit=limit,
	)
	count = len(rows)
	if count == limit:
		count = len(
			frappe.get_list(doctype, filters=filters, or_filters=or_filters, pluck="name", limit=COUNT_LIMIT)
		)
	for row in rows:
		row["_title"] = row.get(meta.title_field) or row.name if meta.title_field else row.name
		row["_actions"] = [
			i for i, action in enumerate(spec.get("actions") or []) if matches(row, action.get("when"))
		]
		for field in shown:
			df = meta.get_field(field)
			if df and df.fieldtype == "Link" and df.options == "User" and row.get(field):
				row[field] = get_fullname(row[field])
	did = acted_today(spec) if not txt else {}
	for row in rows:
		row["_did"] = did.get(row.name)
	return {
		"rows": rows,
		"count": count,
		"fields": form_fields(doctype, shown),
		"actions": [
			{
				"label": action["label"],
				"fields": form_fields(doctype, action.get("fields") or []),
				"comment": action.get("comment"),
				"reply": action.get("reply"),
				"steps": steps(action, meta),
			}
			for action in spec.get("actions") or []
		],
		"done": [] if txt else queue_done(spec, {row.name for row in rows}, did),
	}


def queued_assignments() -> set[str]:
	"""The DocTypes whose records a queue on the user's Home already lists as theirs, by assignment."""
	from frappe.ai.spaces import home_slices

	return {
		widget["doctype"]
		for widget in workspace(personal_default=[]) + home_slices()
		if widget["type"] == "queue"
		and "@me" in frappe.as_json((widget.get("filters") or {}).get("_assign") or "")
	}


def inbox(skip: set[str] | tuple = ()) -> list[dict[str, Any]]:
	"""What waits on the user; assignments of the DocTypes in `skip` are left to the queues that show them."""
	from frappe.model.workflow import get_transitions

	items = []
	for todo in frappe.get_list(
		"ToDo",
		filters={"allocated_to": frappe.session.user, "status": "Open"},
		fields=["name", "description", "reference_type", "reference_name", "date", "priority", "modified"],
		order_by="modified desc",
		limit=INBOX_LIMIT,
	):
		if todo.reference_type in skip:
			continue
		doc = referenced(todo.reference_type, todo.reference_name)
		text = strip_html(todo.description or "")
		items.append(
			{
				"kind": "assignment",
				"name": todo.name,
				# frappe writes "Assignment for <DocType> <name>" when the assigner says nothing
				"text": ""
				if doc and text.startswith(_("Assignment for {0}").format(_(doc.doctype)))
				else text,
				"doctype": todo.reference_type,
				"record": todo.reference_name,
				"title": title_of(doc) if doc else None,
				"who": _("Assigned by {0}").format(get_fullname(todo.assigned_by))
				if todo.assigned_by
				else None,
				"facts": [fact["value"] for fact in facts(doc, 2)] if doc else [],
				"due": todo.date,
				"modified": todo.modified,
				"actions": [
					{
						"label": _("Mark done"),
						"comment": "optional",
						"steps": [_("Closes your assignment"), _("Adds your note as a comment")],
					}
				],
			}
		)
	approvals = (
		frappe.get_list(
			"Workflow Action",
			filters={"status": "Open"},
			fields=["name", "reference_doctype", "reference_name", "workflow_state", "modified"],
			order_by="modified desc",
			limit=INBOX_LIMIT,
		)
		if frappe.has_permission("Workflow Action", "read")
		else []
	)
	for pending in approvals:
		if not frappe.db.exists(pending.reference_doctype, pending.reference_name):
			continue
		doc = frappe.get_doc(pending.reference_doctype, pending.reference_name)
		try:
			actions = list(dict.fromkeys(t.action for t in get_transitions(doc)))
		except frappe.ValidationError:
			actions = []
		if not actions:
			continue
		items.append(
			{
				"kind": "approval",
				"name": pending.name,
				"text": "",
				"doctype": pending.reference_doctype,
				"record": pending.reference_name,
				"title": title_of(doc),
				"who": _("{0} from {1}").format(_(doc.doctype), requester(doc)),
				"facts": [fact["value"] for fact in facts(doc, 2)],
				"modified": pending.modified,
				"actions": [
					{
						"label": action,
						"comment": "required" if needs_reason(action) else "optional",
						"steps": [
							_("{0} moves to {1}").format(_(doc.doctype), next_state(doc, action)),
							_("Adds your note as a comment"),
						],
					}
					for action in actions
				],
			}
		)
	for mention in frappe.get_list(
		"Notification Log",
		filters={"for_user": frappe.session.user, "type": "Mention", "read": 0},
		fields=["name", "subject", "document_type", "document_name", "from_user", "modified"],
		order_by="modified desc",
		limit=INBOX_LIMIT,
	):
		items.append(
			{
				"kind": "mention",
				"name": mention.name,
				"text": strip_html(mention.subject or ""),
				"doctype": mention.document_type,
				"record": mention.document_name,
				"title": reference_title(mention.document_type, mention.document_name),
				"who": get_fullname(mention.from_user) if mention.from_user else None,
				"facts": [],
				"modified": mention.modified,
				"actions": [
					{"label": _("Mark read"), "comment": None, "steps": [_("Marks the mention read")]}
				],
			}
		)
	items.sort(key=lambda item: item["modified"], reverse=True)
	return items


def acted_today(spec: dict[str, Any]) -> dict[str, dict[str, Any]]:
	"""What the user did today with the queue's actions, by record: their latest change that set
	what one of the actions sets, said in the fields the actions touch, and when."""
	from frappe.model.workflow import get_workflow_name, get_workflow_state_field

	doctype, actions = spec["doctype"], spec.get("actions") or []
	outcomes = {
		(action["field"], str(resolve(action["value"]))) for action in actions if action["kind"] == "set"
	}
	workflow = get_workflow_name(doctype) if any(action["kind"] == "workflow" for action in actions) else None
	state = get_workflow_state_field(workflow) if workflow else None
	touched = (
		{field for field, _value in outcomes}
		| {state}
		| {field for action in actions for field in action.get("fields") or []}
	)
	did = {}
	for version in frappe.get_all(
		"Version",
		filters={"ref_doctype": doctype, "owner": frappe.session.user, "creation": (">=", nowdate())},
		fields=["docname", "data", "creation"],
		order_by="creation desc",
		limit=100,
	):
		if version.docname in did:
			continue
		changed = json.loads(version.data).get("changed") or []
		if any((field, str(new)) in outcomes or (state and field == state) for field, _old, new in changed):
			did[version.docname] = {"what": changes(doctype, changed, touched), "when": version.creation}
	return did


def queue_done(
	spec: dict[str, Any], waiting: set[str], did: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
	"""The records the user moved on today with one of the queue's actions, and that no longer
	wait in it, latest first, each with what was done and whether it can be undone."""
	doctype = spec["doctype"]
	done = {name: entry for name, entry in did.items() if name not in waiting}
	taken = (
		taken_today(doctype)
		if any(action["kind"] == "assign" for action in spec.get("actions") or [])
		else {}
	)
	for name, when in taken.items():
		if name not in waiting and name not in done:
			done[name] = {"what": _("Taken by you"), "when": when}
	meta = frappe.get_meta(doctype)
	titles = {
		row.name: (row.get(meta.title_field) or row.name) if meta.title_field else row.name
		for row in frappe.get_list(
			doctype,
			filters={"name": ("in", list(done) or [""])},
			fields=["name", *([meta.title_field] if meta.title_field else [])],
		)
	}
	entries = [
		{"name": name, "title": titles[name], **entry, "undo": bool(undoable(doctype, name) or name in taken)}
		for name, entry in done.items()
		if name in titles
	]
	return sorted(entries, key=lambda entry: entry["when"], reverse=True)[:DONE_LIMIT]


def inbox_done() -> list[dict[str, Any]]:
	"""The assignments the user marked done today, and the approvals they decided."""
	today, user = nowdate(), frappe.session.user
	entries = [
		{
			"kind": "assignment",
			"name": todo.name,
			"title": reference_title(todo.reference_type, todo.reference_name)
			or strip_html(todo.description or ""),
			"what": _("Marked done"),
			"when": todo.modified,
			"undo": True,
		}
		for todo in frappe.get_all(
			"ToDo",
			filters={"allocated_to": user, "status": "Closed", "modified": (">=", today)},
			fields=["name", "reference_type", "reference_name", "description", "modified"],
			order_by="modified desc",
			limit=DONE_LIMIT,
		)
	]
	from frappe.model.workflow import get_workflow_name, get_workflow_state_field

	for decided in frappe.get_all(
		"Workflow Action",
		filters={"status": "Completed", "completed_by": user, "modified": (">=", today)},
		fields=["name", "reference_doctype", "reference_name", "modified"],
		order_by="modified desc",
		limit=DONE_LIMIT,
	):
		doc = referenced(decided.reference_doctype, decided.reference_name)
		if not doc:
			continue
		workflow = get_workflow_name(doc.doctype)
		state = doc.get(get_workflow_state_field(workflow)) if workflow else None
		entries.append(
			{
				"kind": "approval",
				"name": decided.name,
				"title": title_of(doc),
				"what": _("Now {0}").format(_(state)) if state else _("Decided"),
				"when": decided.modified,
				"undo": False,
			}
		)
	return sorted(entries, key=lambda entry: entry["when"], reverse=True)[:DONE_LIMIT]


def taken_today(doctype: str, names: list[str] | None = None) -> dict[str, Any]:
	"""The records of `doctype` the user assigned to themselves today and still holds, with when."""
	filters = {
		"reference_type": doctype,
		"allocated_to": frappe.session.user,
		"assigned_by": frappe.session.user,
		"status": "Open",
		"creation": (">=", nowdate()),
	}
	if names is not None:
		filters["reference_name"] = ("in", names or [""])
	return {
		todo.reference_name: todo.creation
		for todo in frappe.get_all("ToDo", filters=filters, fields=["reference_name", "creation"])
	}


def undoable(doctype: str, name: str) -> list[list[Any]]:
	"""The fields of the user's last change today to the record, as [field, old, new]; a workflow's
	state is left out, since only its actions move it."""
	from frappe.model.workflow import get_workflow_name, get_workflow_state_field

	last = frappe.get_all(
		"Version",
		filters={
			"ref_doctype": doctype,
			"docname": name,
			"owner": frappe.session.user,
			"creation": (">=", nowdate()),
		},
		pluck="data",
		order_by="creation desc",
		limit=1,
	)
	if not last:
		return []
	workflow = get_workflow_name(doctype)
	state = get_workflow_state_field(workflow) if workflow else None
	meta = frappe.get_meta(doctype)
	return [
		change
		for change in json.loads(last[0]).get("changed") or []
		if change[0] != state and meta.get_field(change[0])
	]


def changes(doctype: str, changed: list[list[Any]], fields: set[str]) -> str:
	"""A change to `fields` as the user reads it: 'Status → Planned, Release → v17'."""
	meta = frappe.get_meta(doctype)
	said = []
	for field, _old, new in changed:
		df = meta.get_field(field)
		if df and not df.hidden and field in fields:
			said.append(f"{_(df.label)} → {display(df, new) if new not in (None, '') else '—'}")
	return ", ".join(said) or _("Updated")


def steps(action: dict[str, Any], meta) -> list[str]:
	"""What an action does, one step at a time, as the task card says it before it runs."""
	said = []
	if action.get("reply"):
		said.append(_("Emails your reply to {0}").format(_(meta.get_field(action["reply"]).label)))
	if action.get("fields"):
		labels = [_(meta.get_field(field).label) for field in action["fields"] if meta.get_field(field)]
		said.append(_("Saves {0}").format(", ".join(labels)))
	kind = action["kind"]
	if kind == "set":
		value = _("you") if action["value"] == "@me" else _(str(action["value"]))
		said.append(_("Sets {0} to {1}").format(_(meta.get_field(action["field"]).label), value))
	elif kind == "assign":
		said.append(_("Assigns it to you"))
	elif kind == "workflow":
		said.append(_("Applies {0}").format(_(action["action"])))
	else:
		said.append(_("Creates a {0} from it").format(_(action["doctype"])))
	if action.get("comment"):
		said.append(_("Adds your note as a comment"))
	return said


def send_reply(doc, field: str, text: str) -> None:
	"""Email `text` to the address in the record's `field`, on the record's thread."""
	from frappe.core.doctype.communication.email import make

	recipient = doc.get(field)
	if not recipient:
		frappe.throw(
			_("{0} has no {1} to reply to.").format(title_of(doc), _(doc.meta.get_field(field).label))
		)
	make(
		doctype=doc.doctype,
		name=doc.name,
		content=frappe.utils.escape_html(text).replace("\n", "<br>"),
		subject=_("Re: {0}").format(title_of(doc)),
		recipients=recipient,
		send_email=True,
	)


def needs_reason(action: str | None) -> bool:
	"""Whether a workflow action turns a request down, and so needs a reason."""
	return bool(re.search(r"reject|decline|deny|refuse", action or "", re.IGNORECASE))


def next_state(doc, action: str) -> str:
	from frappe.model.workflow import get_transitions

	for transition in get_transitions(doc):
		if transition.action == action:
			return _(transition.next_state)
	return _(action)


def own_todo(name: str):
	todo = frappe.get_doc("ToDo", name)
	if todo.allocated_to != frappe.session.user:
		frappe.throw(_("This is not your assignment."), frappe.PermissionError)
	return todo


def referenced(doctype: str | None, name: str | None):
	"""The record an assignment or approval is about, if it is there and the user may read it."""
	if not doctype or not name or not frappe.db.exists(doctype, name):
		return None
	doc = frappe.get_doc(doctype, name)
	return doc if doc.has_permission("read") else None


def requester(doc) -> str:
	"""Who a record comes from: the person who raised or requested it, else whoever made it."""
	for field in REQUESTER_FIELDS:
		value = doc.get(field) if doc.meta.get_field(field) else None
		if value:
			return get_fullname(value) if frappe.db.exists("User", value) else str(value)
	return get_fullname(doc.owner)


def facts(doc, limit: int = 4) -> list[dict[str, str]]:
	"""What is at stake on a record: its list view's fields, but its title, as label and value."""
	meta = doc.meta
	said = []
	for df in meta.fields:
		if not df.in_list_view or df.fieldname == meta.title_field or df.fieldtype in LONG_TEXT:
			continue
		value = doc.get(df.fieldname)
		if value not in (None, "", 0):
			said.append({"label": _(df.label), "value": display(df, value, doc)})
	return said[:limit]


def display(df, value: Any, doc=None) -> str:
	if df.fieldtype == "Link" and df.options == "User":
		return get_fullname(value)
	return strip_html(str(frappe.format_value(value, df, doc)))


def long_text(doc) -> str | None:
	for df in doc.meta.fields:
		if df.fieldtype in LONG_TEXT and not df.hidden and doc.get(df.fieldname):
			text = strip_html(doc.get(df.fieldname)).strip()
			if text:
				return text[:TEXT_LIMIT]
	return None


def timeline(doc, limit: int = 4) -> list[dict[str, Any]]:
	"""The latest comments and emails on a record, oldest first."""
	on = {"reference_doctype": doc.doctype, "reference_name": doc.name}
	entries = [
		{"who": get_fullname(row.owner), "when": row.creation, "text": row.content, "kind": "comment"}
		for row in frappe.get_all(
			"Comment",
			filters={**on, "comment_type": "Comment"},
			fields=["owner", "content", "creation"],
			order_by="creation desc",
			limit=limit,
		)
	]
	entries += [
		{
			"who": row.sender_full_name or row.sender,
			"when": row.creation,
			"text": row.content,
			"kind": "email",
		}
		for row in frappe.get_all(
			"Communication",
			filters={**on, "communication_type": "Communication"},
			fields=["sender", "sender_full_name", "content", "creation"],
			order_by="creation desc",
			limit=limit,
		)
	]
	entries = sorted(entries, key=lambda entry: entry["when"], reverse=True)[:limit]
	return [
		{**entry, "text": strip_html(entry["text"] or "").strip()[:NOTE_LIMIT]} for entry in reversed(entries)
	]


def form_fields(doctype: str, fieldnames: list[str]) -> list[dict[str, Any]]:
	meta = frappe.get_meta(doctype)
	fields = []
	for fieldname in fieldnames:
		if fieldname in STANDARD_FIELDS and fieldname != "name":
			fields.append({"fieldname": fieldname, **STANDARD_FIELDS[fieldname], "read_only": 1})
			continue
		df = meta.get_field(fieldname)
		if not df or df.fieldtype in table_fields or df.fieldtype not in data_fieldtypes:
			continue
		fields.append(
			{
				"fieldname": df.fieldname,
				"label": _(df.label or df.fieldname),
				"fieldtype": df.fieldtype,
				"options": df.options,
				"reqd": df.reqd,
				"read_only": df.read_only or df.permlevel > 0,
				"default": df.default,
			}
		)
	return fields


def order_by(given: str | None, meta) -> str:
	if given:
		field, _sep, direction = given.strip().partition(" ")
		if (meta.get_field(field) or field in ("name", "modified", "creation")) and direction.lower() in (
			"",
			"asc",
			"desc",
		):
			return f"{field} {direction or 'asc'}"
	return "modified desc"


def resolve(value: Any) -> Any:
	"""Filters and values with '@me' as the person, also inside a pattern such as '%@me%', and
	'@today' as today's date."""
	if isinstance(value, dict):
		return {key: resolve(item) for key, item in value.items()}
	if isinstance(value, list):
		return [resolve(item) for item in value]
	if value == "@today":
		return nowdate()
	if isinstance(value, str) and "@me" in value:
		return value.replace("@me", frappe.session.user)
	return value


def fill(value: Any, doc) -> Any:
	"""A create action's value, with '{field}' as the row's field."""
	if not isinstance(value, str):
		return value
	value = resolve(value)
	whole = re.fullmatch(r"\{(\w+)\}", value or "")
	if whole:
		return doc.get(whole.group(1))
	return re.sub(r"\{(\w+)\}", lambda match: str(doc.get(match.group(1)) or ""), value)


def matches(row: dict[str, Any], when: dict[str, Any] | None) -> bool:
	return all(
		str(row.get(field) if row.get(field) is not None else "") == str(value)
		for field, value in (when or {}).items()
	)


def can(ptype: str, spec: dict[str, Any]) -> bool:
	return bool(frappe.has_permission(spec["doctype"], ptype))


def readable(spec: dict[str, Any]) -> bool:
	return bool(
		frappe.db.exists(spec["doctype"], spec["name"])
		and frappe.has_permission(spec["doctype"], "read", spec["name"])
	)


def title_of(doc) -> str:
	field = doc.meta.title_field
	return str(doc.get(field) or doc.name) if field else doc.name


def reference_title(doctype: str | None, name: str | None) -> str | None:
	if not doctype or not name or not frappe.db.exists(doctype, name):
		return None
	return title_of(frappe.get_doc(doctype, name))


def number_card(name: str) -> dict[str, Any]:
	"""A desk Number Card's value, as the desk computes it, or None for a kind it leaves to a report."""
	from frappe.desk.doctype.number_card.number_card import get_result

	card = frappe.get_doc("Number Card", name)
	value = None
	if card.type == "Custom" and card.method:
		value = frappe.call(card.method, filters=card.filters_json)
	elif card.type == "Document Type" and frappe.has_permission(card.document_type, "read"):
		value = get_result(card.as_dict(), card.filters_json)
	if isinstance(value, dict):
		value = value.get("value")
	# a count is a number of records; only a sum or an average of money is money
	money = card.function != "Count" and card.currency
	return {"label": _(card.label), "value": value, "currency": money or None}


def dashboard_chart(name: str) -> dict[str, Any]:
	"""A desk Dashboard Chart's labels and series, as the desk computes them."""
	from frappe.desk.doctype.dashboard_chart.dashboard_chart import get

	chart = frappe.get_doc("Dashboard Chart", name)
	data = get(chart_name=name) or {}
	return {
		"label": _(chart.chart_name),
		"type": chart.type,
		"labels": data.get("labels") or [],
		"datasets": data.get("datasets") or [],
	}
