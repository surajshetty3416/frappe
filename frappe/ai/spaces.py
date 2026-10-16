# Copyright (c) 2026, Frappe Technologies and contributors
# License: MIT. See LICENSE

"""Spaces: where a team does its work together. A Space is a public Workspace with people in it
(Space Member) and widgets to work in. A Workspace an app ships is a Space as it is: its number
cards, charts and quick lists become widgets, and its shortcuts and links are left to search. A
Space that sets `widgets` shows those instead.

A widget marked `home` is the Space's slice of a member's Home, so a person's Home is ready the
moment they join their Spaces.

Apps take part through two hooks:
- `space_templates`: functions that return the Spaces an app offers to set up, each a dict of
  name, title, icon, description, roles and widgets.
- `space_conversation`: a function that takes a Space's name and gives what fills its
  conversation, {"provider", "url"}, or None; the last app's answer that is not None wins. Without
  one, a Space shows the activity on the records its widgets show. An app that keeps its light or
  dark theme in localStorage adds "theme_key", and the shell writes its own theme there first."""

from __future__ import annotations

import json
from typing import Any

import frappe
from frappe import _
from frappe.utils import get_fullname

ACTIVITY_LIMIT = 30


@frappe.whitelist()
def get_spaces() -> dict[str, list[dict[str, Any]]]:
	"""The Spaces the user is in, and the others they can see and join."""
	joined = set(my_space_names())
	spaces = visible_spaces()
	counts = member_counts([space["name"] for space in spaces])
	for space in spaces:
		space["members"] = counts.get(space["name"], 0)
	return {
		"mine": [space for space in spaces if space["name"] in joined],
		"others": [space for space in spaces if space["name"] not in joined],
	}


@frappe.whitelist()
def get_space(space: str) -> dict[str, Any]:
	"""A Space as its page shows it: its widgets, its people and what fills its conversation."""
	from frappe.ai.workspace import with_charts

	doc = permitted(space)
	members = frappe.get_all("Space Member", filters={"space": space}, pluck="user")
	return {
		"name": doc.name,
		"title": doc.title,
		"icon": doc.icon,
		"description": doc.description,
		"widgets": with_charts([{**widget, "space": doc.name} for widget in space_widgets(doc)]),
		"members": [
			{
				"user": user,
				"full_name": get_fullname(user),
				"image": frappe.db.get_value("User", user, "user_image"),
			}
			for user in members
		],
		"joined": frappe.session.user in members,
		"can_edit": can_edit(),
		"conversation": conversation(doc.name),
	}


@frappe.whitelist(methods=["POST"])
def join_space(space: str) -> None:
	permitted(space)
	if not frappe.db.exists("Space Member", {"space": space, "user": frappe.session.user}):
		frappe.get_doc({"doctype": "Space Member", "space": space, "user": frappe.session.user}).insert()


@frappe.whitelist(methods=["POST"])
def leave_space(space: str) -> None:
	for name in frappe.get_all(
		"Space Member", filters={"space": space, "user": frappe.session.user}, pluck="name"
	):
		frappe.delete_doc("Space Member", name)


@frappe.whitelist(methods=["POST"])
def save_space_widgets(space: str, widgets: list[dict[str, Any]] | str) -> list[dict[str, Any]]:
	"""Keep `widgets` as the Space's own; an empty list goes back to what its workspace holds."""
	from frappe.ai.workspace import clean

	doc = permitted(space)
	if not can_edit():
		frappe.throw(_("Only a Workspace Manager changes a Space."), frappe.PermissionError)
	widgets = clean(
		[{k: v for k, v in widget.items() if k != "space"} for widget in frappe.parse_json(widgets)]
	)
	doc.widgets = json.dumps(widgets) if widgets else None
	doc.save()
	return widgets


@frappe.whitelist()
def get_activity(space: str) -> list[dict[str, Any]]:
	"""What people said and did lately on the records the Space's widgets show, newest first."""
	doctypes = sorted(
		{widget["doctype"] for widget in space_widgets(permitted(space)) if widget.get("doctype")}
	)
	readable = [doctype for doctype in doctypes if frappe.has_permission(doctype, "read")]
	if not readable:
		return []
	return frappe.get_list(
		"Comment",
		filters={
			"reference_doctype": ("in", readable),
			"comment_type": ("in", ("Comment", "Info", "Workflow")),
		},
		fields=[
			"name",
			"comment_type",
			"reference_doctype",
			"reference_name",
			"content",
			"owner",
			"creation",
		],
		order_by="creation desc",
		limit=ACTIVITY_LIMIT,
	)


def visible_spaces() -> list[dict[str, Any]]:
	spaces = []
	for row in frappe.get_all(
		"Workspace",
		filters={"public": 1, "is_hidden": 0, "type": ("in", ("Workspace", "", None))},
		fields=["name", "title", "icon", "description", "module", "sequence_id"],
		order_by="sequence_id asc, title asc",
	):
		if visible(row):
			spaces.append(row)
	return spaces


def my_space_names() -> list[str]:
	return frappe.get_all(
		"Space Member", filters={"user": frappe.session.user}, pluck="space", order_by="creation asc"
	)


def member_counts(spaces: list[str]) -> dict[str, int]:
	if not spaces:
		return {}
	return dict(
		frappe.get_all(
			"Space Member",
			filters={"space": ("in", spaces)},
			fields=["space", {"COUNT": "*", "as": "count"}],
			group_by="space",
			as_list=True,
		)
	)


def permitted(space: str):
	doc = frappe.get_doc("Workspace", space)
	if not doc.public or not visible(doc):
		frappe.throw(_("You cannot see this Space."), frappe.PermissionError)
	return doc


def visible(workspace) -> bool:
	"""Whether the user may see the workspace, by its module and roles, as the desk decides."""
	from frappe.desk.desktop import Workspace
	from frappe.model.document import Document

	return Workspace(
		workspace.as_dict() if isinstance(workspace, Document) else workspace, minimal=True
	).is_permitted()


def space_widgets(doc) -> list[dict[str, Any]]:
	"""The Space's own widgets, or the ones its workspace's number cards, quick lists and charts make."""
	if doc.get("widgets"):
		return frappe.parse_json(doc.widgets)
	widgets = [
		{
			"id": f"card-{row.idx}",
			"type": "number_card",
			"title": row.label,
			"number_card": row.number_card_name,
			"size": "s",
		}
		for row in doc.number_cards
	]
	widgets += [
		{
			"id": f"list-{row.idx}",
			"type": "queue",
			"title": row.label or row.document_type,
			"doctype": row.document_type,
			"filters": frappe.parse_json(row.quick_list_filter or "[]"),
			"size": "s",
		}
		for row in doc.quick_lists
	]
	widgets += [
		{
			"id": f"chart-{row.idx}",
			"type": "dashboard_chart",
			"title": row.label,
			"dashboard_chart": row.chart_name,
			"size": "s",
		}
		for row in doc.charts
	]
	return widgets


def home_slices() -> list[dict[str, Any]]:
	"""Each of the user's Spaces' widgets for their Home, the Space named on each."""
	slices = []
	for name in my_space_names():
		try:
			doc = permitted(name)
		except frappe.PermissionError:
			continue
		slices += [
			{**widget, "space": doc.name, "space_title": doc.title}
			for widget in space_widgets(doc)
			if widget.get("home")
		]
	return slices


def conversation(space: str) -> dict[str, Any] | None:
	found = None
	for method in frappe.get_hooks("space_conversation"):
		found = frappe.get_attr(method)(space) or found
	return found


def templates() -> list[dict[str, Any]]:
	"""Every Space the installed apps offer to set up."""
	offered = []
	for method in frappe.get_hooks("space_templates"):
		offered += frappe.get_attr(method)()
	return offered


def create_space(template: dict[str, Any], members: list[str] | None = None) -> str:
	"""A Space from a template, with the user and `members` in it; its name."""
	from frappe.ai.workspace import clean

	title = template["title"]
	if not frappe.db.exists("Workspace", title):
		frappe.get_doc(
			{
				"doctype": "Workspace",
				"label": title,
				"title": title,
				"public": 1,
				"module": template.get("module") or space_module(),
				"icon": template.get("icon") or "folder-normal",
				"description": template.get("description"),
				"widgets": json.dumps(clean(template.get("widgets") or [])),
				"content": "[]",
				"roles": [{"role": role} for role in template.get("roles") or []],
			}
		).insert()
	for user in dict.fromkeys([frappe.session.user, *(members or [])]):
		if not frappe.db.exists("Space Member", {"space": title, "user": user}):
			frappe.get_doc({"doctype": "Space Member", "space": title, "user": user}).insert()
	return title


def space_module() -> str:
	"""The site's own module for Spaces made on it, which no app ships."""
	if not frappe.db.exists("Module Def", "Spaces"):
		frappe.get_doc(
			{"doctype": "Module Def", "module_name": "Spaces", "custom": 1, "app_name": "frappe"}
		).insert(ignore_permissions=True)
		# a new module gets a page to open on in the desk; Spaces open from the Home, so that page
		# would be an empty Space everyone sees
		if frappe.db.exists("Workspace", "Spaces"):
			frappe.delete_doc("Workspace", "Spaces", ignore_permissions=True, force=True)
	return "Spaces"


def can_edit() -> bool:
	# a Desk User may write their own private pages; a shared Space is a Workspace Manager's to change
	return "Workspace Manager" in frappe.get_roles()
