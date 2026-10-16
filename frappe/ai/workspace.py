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
from frappe.utils import nowdate

WORKSPACE_KEY = "studio_workspace"
SETUP_KEY = "studio_setup_done"
SETUP_CHAT_KEY = "studio_setup_chat"
WELCOMED_KEY = "studio_welcomed"
SITE_SETUP_KEY = "studio_site_setup_done"
ORGANIZATION_KEY = "studio_organization"

QUEUE_LIMIT = 20
INBOX_LIMIT = 30
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
		"{label, kind: 'workflow', action} applies a workflow action; {label, kind: 'create', doctype, "
		"values} creates a record from the row, where '{name}' or '{field}' in a value is the row's. "
		"An action with `when: {field: value}` shows only on rows that match.",
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

DEFAULT_WORKSPACE = [{"type": "inbox", "size": "l"}]


@frappe.whitelist()
def get_workspace() -> dict[str, Any]:
	"""The user's widgets, and what the user still has to set up. A chart widget says its chart's
	type, so the workspace can set numbers apart from charts."""
	from frappe.ai.spaces import home_slices

	user = frappe.session.user
	widgets = workspace() + home_slices()
	charts = [widget["chart"] for widget in widgets if widget["type"] == "chart"]
	types = dict(
		frappe.get_all(
			"Insights Chart v3", filters={"name": ("in", charts)}, fields=["name", "chart_type"], as_list=True
		)
		if charts
		else []
	)
	return {
		"widgets": [
			{**widget, "chart_type": types.get(widget["chart"])} if widget["type"] == "chart" else widget
			for widget in widgets
		],
		"customized": bool(frappe.defaults.get_defaults_for(user).get(WORKSPACE_KEY)),
		"setup": setup_state(),
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
		return {"items": inbox()}
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
def act(widget: str, action: int, name: str, space: str | None = None) -> dict[str, Any]:
	"""Run a queue widget's `action` on the record `name`."""
	spec = find_widget(widget, space)
	if spec["type"] != "queue":
		frappe.throw(_("Only a queue widget acts on its records."))
	try:
		button = spec["actions"][int(action)]
	except (IndexError, TypeError, ValueError):
		frappe.throw(_("This widget has no such action."))
	doc = frappe.get_doc(spec["doctype"], name)
	if button["kind"] == "set":
		doc.check_permission("write")
		doc.set(button["field"], resolve(button["value"]))
		doc.save()
		return {"doctype": doc.doctype, "name": doc.name}
	if button["kind"] == "workflow":
		from frappe.model.workflow import apply_workflow

		doc.check_permission("read")
		apply_workflow(doc, button["action"])
		return {"doctype": doc.doctype, "name": doc.name}
	values = {field: fill(value, doc) for field, value in (button.get("values") or {}).items()}
	made = frappe.get_doc({"doctype": button["doctype"], **values}).insert()
	return {"doctype": made.doctype, "name": made.name}


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


@frappe.whitelist(methods=["POST"])
def respond(kind: str, name: str, action: str | None = None) -> None:
	"""Act on an inbox item: close an assignment, mark a mention read, or apply a workflow action
	to the record an approval waits on."""
	if kind == "mention":
		from frappe.desk.doctype.notification_log.notification_log import mark_as_read

		mark_as_read(name)
		return
	if kind == "assignment":
		todo = frappe.get_doc("ToDo", name)
		if todo.allocated_to != frappe.session.user:
			frappe.throw(_("This is not your assignment."), frappe.PermissionError)
		todo.status = "Closed"
		todo.save(ignore_permissions=True)
		return
	from frappe.model.workflow import apply_workflow

	pending = frappe.get_doc("Workflow Action", name)
	pending.check_permission("read")
	apply_workflow(frappe.get_doc(pending.reference_doctype, pending.reference_name), action)


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
		"fields": fields,
		"values": {field["fieldname"]: doc.get(field["fieldname"]) for field in fields},
		"can_write": can_write,
		"transitions": transitions,
		"modified": doc.modified,
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


def workspace() -> list[dict[str, Any]]:
	saved = frappe.defaults.get_user_default(WORKSPACE_KEY)
	return json.loads(saved) if saved else clean(DEFAULT_WORKSPACE)


def find_widget(widget: str, space: str | None = None) -> dict[str, Any]:
	from frappe.ai.spaces import permitted, space_widgets

	widgets = space_widgets(permitted(space)) if space else workspace()
	found = next((spec for spec in widgets if spec["id"] == widget), None)
	if not found:
		frappe.throw(_("This widget is no longer on your workspace."))
	return found


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
		if not meta.get_field(field) and field != "name":
			frappe.throw(
				_("{0} has no field {1}.").format(widget["doctype"], field), title=_("Invalid Widget")
			)
	for action in widget.get("actions") or []:
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
		elif action.get("kind") != "workflow" or not action.get("action"):
			frappe.throw(_("An action is set, workflow or create."), title=_("Invalid Widget"))
		if not action.get("label"):
			frappe.throw(_("An action needs a label."), title=_("Invalid Widget"))


def queue_rows(spec: dict[str, Any], txt: str | None) -> dict[str, Any]:
	doctype = spec["doctype"]
	if not frappe.has_permission(doctype, "read"):
		return {"rows": [], "count": 0, "fields": [], "denied": True}
	meta = frappe.get_meta(doctype)
	shown = [field for field in spec.get("fields") or [] if field != "name"]
	when = {field for action in spec.get("actions") or [] for field in (action.get("when") or {})}
	columns = list(dict.fromkeys(["name", *([meta.title_field] if meta.title_field else []), *shown, *when]))
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
	return {"rows": rows, "count": count, "fields": form_fields(doctype, shown)}


def inbox() -> list[dict[str, Any]]:
	from frappe.model.workflow import get_transitions

	items = []
	for todo in frappe.get_list(
		"ToDo",
		filters={"allocated_to": frappe.session.user, "status": "Open"},
		fields=["name", "description", "reference_type", "reference_name", "date", "priority", "modified"],
		order_by="modified desc",
		limit=INBOX_LIMIT,
	):
		items.append(
			{
				"kind": "assignment",
				"name": todo.name,
				"text": frappe.utils.strip_html(todo.description or ""),
				"doctype": todo.reference_type,
				"record": todo.reference_name,
				"title": reference_title(todo.reference_type, todo.reference_name),
				"due": todo.date,
				"priority": todo.priority,
				"modified": todo.modified,
				"actions": ["Done"],
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
				"text": _("{0} is {1}").format(_(pending.reference_doctype), pending.workflow_state),
				"doctype": pending.reference_doctype,
				"record": pending.reference_name,
				"title": title_of(doc),
				"modified": pending.modified,
				"actions": actions,
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
				"text": frappe.utils.strip_html(mention.subject or ""),
				"doctype": mention.document_type,
				"record": mention.document_name,
				"title": reference_title(mention.document_type, mention.document_name),
				"modified": mention.modified,
				"actions": ["Mark read"],
			}
		)
	items.sort(key=lambda item: item["modified"], reverse=True)
	return items


def form_fields(doctype: str, fieldnames: list[str]) -> list[dict[str, Any]]:
	meta = frappe.get_meta(doctype)
	fields = []
	for fieldname in fieldnames:
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
	"""Filters and values with '@me' as the person and '@today' as today's date."""
	if isinstance(value, dict):
		return {key: resolve(item) for key, item in value.items()}
	if isinstance(value, list):
		return [resolve(item) for item in value]
	if value == "@me":
		return frappe.session.user
	if value == "@today":
		return nowdate()
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
	return {"label": _(card.label), "value": value, "currency": card.currency}


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
