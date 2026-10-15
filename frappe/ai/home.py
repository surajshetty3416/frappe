# Copyright (c) 2026, Frappe Technologies and contributors
# License: MIT. See LICENSE

"""The home, where a person who uses what was built finds it, opens it and pins what they come back
to. A layer lists its artifacts here by naming, under the `view` key of its `studio_artifacts` hook,
a function that takes an artifact's name and gives the path where a person uses it, or None while
there is nothing to use yet.

The home is a list of sections, top to bottom. Each person may arrange their own, by hand or by
asking the assistant; until they do, they get the one a System Manager set for everyone, or
DEFAULT_LAYOUT."""

from __future__ import annotations

import json
from typing import Annotated, Any

import frappe
from frappe import _
from frappe.ai.artifacts import artifact, artifact_types
from frappe.ai.lib.tool import ToolContext, tool

RECENT_LIMIT = 12
LIST_LIMIT = 24
LAYOUT_KEY = "studio_home_layout"

# what each section shows, and the keys it takes besides `type` and an optional `title`
SECTIONS = {
	"pinned": ("The artifacts the person pinned", ()),
	"recent": ("The artifacts changed last", ()),
	"browse": ("A tile for each kind of artifact, to browse all of that kind", ()),
	"list": ("Every artifact of one DocType", ("doctype",)),
	"views": ("Artifacts picked by hand", ("items",)),
	"embed": ("One artifact, shown in the page as it is used", ("doctype", "name")),
}
DEFAULT_LAYOUT = [{"type": "pinned"}, {"type": "recent"}, {"type": "browse"}]


def viewable() -> dict[str, dict[str, str]]:
	return {doctype: spec for doctype, spec in artifact_types().items() if spec.get("view")}


@frappe.whitelist()
def get_home() -> dict[str, Any]:
	"""The user's home, each section with what it shows, and what the user may do with it."""
	return {
		"sections": [{**section, **section_data(section)} for section in layout()],
		"pinned": artifacts(pinned=True),
		"customized": bool(frappe.defaults.get_defaults_for(frappe.session.user).get(LAYOUT_KEY)),
		"can_build": any(frappe.has_permission(doctype, "create") for doctype in viewable()),
		"can_set_default": "System Manager" in frappe.get_roles(),
	}


@frappe.whitelist(methods=["POST"])
def save_home_layout(
	sections: list[dict[str, Any]] | str, for_everyone: bool = False
) -> list[dict[str, Any]]:
	"""Keep `sections` as the user's home, or, for a System Manager, as everyone's who has not
	arranged their own."""
	sections = clean(frappe.parse_json(sections))
	value = json.dumps(sections)
	if frappe.utils.sbool(for_everyone):
		frappe.only_for("System Manager")
		frappe.defaults.set_global_default(LAYOUT_KEY, value)
	else:
		frappe.defaults.set_user_default(LAYOUT_KEY, value)
	frappe.publish_realtime("studio_home", user=frappe.session.user, after_commit=True)
	return sections


@frappe.whitelist(methods=["POST"])
def reset_home_layout() -> None:
	"""Give the user the home everyone gets again."""
	frappe.defaults.clear_user_default(LAYOUT_KEY)
	frappe.publish_realtime("studio_home", user=frappe.session.user, after_commit=True)


@frappe.whitelist()
def get_view(doctype: str, name: str) -> dict[str, Any]:
	"""One artifact as the home opens it: where it is used, and whether the user may edit it."""
	spec = viewable().get(doctype)
	if not spec:
		frappe.throw(_("{0} cannot be opened from the home.").format(doctype))
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("read")
	return {
		**artifact(doctype, name, doc.get(spec["title_field"])),
		"modified": doc.modified,
		"view": frappe.get_attr(spec["view"])(name),
		"can_write": bool(doc.has_permission("write")),
		"pinned": frappe.session.user in json.loads(doc.get("_liked_by") or "[]"),
	}


@tool
def get_home_layout(*, ctx: ToolContext) -> dict[str, Any]:
	"""The person's home page (/home) as a list of sections, top to bottom, with the section types
	it can hold and the artifacts the person can put on it."""
	return {
		"sections": layout(),
		"section_types": {kind: {"shows": shows, "keys": keys} for kind, (shows, keys) in SECTIONS.items()},
		"artifacts": artifacts(limit=100),
	}


@tool
def set_home_layout(
	sections: Annotated[
		list[dict[str, Any]],
		"Every section of the home, top to bottom, each {type, title?, ...the keys its type takes}; "
		"keep the `id` of a section that stays. An `items` entry is {doctype, name}.",
	],
	*,
	ctx: ToolContext,
) -> list[dict[str, Any]]:
	"""Rearrange the person's own home page (/home): add, remove, retitle or reorder its sections.
	Read it with get_home_layout first, and send the whole list back. The home on their screen
	updates at once."""
	return save_home_layout(sections)


def layout() -> list[dict[str, Any]]:
	saved = frappe.defaults.get_user_default(LAYOUT_KEY)
	return json.loads(saved) if saved else clean(DEFAULT_LAYOUT)


def clean(sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
	"""Sections as the home keeps them: known types with the keys they take, each with an id."""
	types = viewable()
	cleaned = []
	for section in sections:
		kind = section.get("type")
		if kind not in SECTIONS:
			frappe.throw(_("The home has no section of type {0}.").format(kind), title=_("Invalid Section"))
		row = {
			"id": section.get("id") or frappe.generate_hash(length=8),
			"type": kind,
			"title": section.get("title") or None,
		}
		for key in SECTIONS[kind][1]:
			row[key] = section.get(key)
		doctypes = (
			[row["doctype"]] if "doctype" in row else [item.get("doctype") for item in row.get("items") or []]
		)
		for doctype in doctypes:
			if doctype not in types:
				frappe.throw(
					_("{0} cannot be shown on the home.").format(doctype), title=_("Invalid Section")
				)
		if kind == "embed" and not row["name"]:
			frappe.throw(
				_("An embedded section needs the name of what it shows."), title=_("Invalid Section")
			)
		cleaned.append(row)
	return cleaned


def section_data(section: dict[str, Any]) -> dict[str, Any]:
	kind = section["type"]
	if kind == "pinned":
		return {"artifacts": artifacts(pinned=True)}
	if kind == "recent":
		return {"artifacts": artifacts(limit=RECENT_LIMIT)}
	if kind == "list":
		return {"artifacts": artifacts(doctypes=[section["doctype"]], limit=LIST_LIMIT)}
	if kind == "views":
		return {"artifacts": [found for item in section["items"] if (found := readable(item))]}
	if kind == "embed":
		return {"view": get_view(section["doctype"], section["name"]) if readable(section) else None}
	return {}


def readable(item: dict[str, Any]) -> dict[str, Any] | None:
	doctype, name = item.get("doctype"), item.get("name")
	if not frappe.db.exists(doctype, name) or not frappe.has_permission(doctype, "read", name):
		return None
	modified, title = frappe.db.get_value(doctype, name, ["modified", viewable()[doctype]["title_field"]])
	return {**artifact(doctype, name, title), "modified": modified}


def artifacts(
	pinned: bool = False, limit: int | None = None, doctypes: list[str] | None = None
) -> list[dict[str, Any]]:
	found = []
	for doctype, spec in viewable().items():
		if doctypes and doctype not in doctypes:
			continue
		if not frappe.has_permission(doctype, "read"):
			continue
		if pinned and not frappe.db.has_column(doctype, "_liked_by"):
			continue
		title_field = spec["title_field"]
		for record in frappe.get_list(
			doctype,
			filters=[["_liked_by", "like", f'%"{frappe.session.user}"%']] if pinned else [],
			fields=["name", title_field, "modified"],
			order_by="modified desc",
			limit=limit,
		):
			found.append(
				{**artifact(doctype, record.name, record.get(title_field)), "modified": record.modified}
			)
	found.sort(key=lambda row: row["modified"], reverse=True)
	return found[:limit] if limit else found
