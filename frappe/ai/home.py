# Copyright (c) 2026, Frappe Technologies and contributors
# License: MIT. See LICENSE

"""The home, where a person finds what was built, opens it to use it and pins what they come back to.
A layer lists its artifacts here by naming, under the `view` key of its `studio_artifacts` hook, a
function that takes an artifact's name and gives the path where a person uses it, or None while
there is nothing to use yet. What the home shows is the person's workspace (frappe.ai.workspace)."""

from __future__ import annotations

import json
from typing import Any

import frappe
from frappe import _
from frappe.ai.artifacts import artifact, artifact_types


def viewable() -> dict[str, dict[str, str]]:
	return {doctype: spec for doctype, spec in artifact_types().items() if spec.get("view")}


@frappe.whitelist()
def get_home() -> dict[str, Any]:
	"""The artifacts the user pinned, and whether the user can build any."""
	return {
		"pinned": artifacts(pinned=True),
		"can_build": any(frappe.has_permission(doctype, "create") for doctype in viewable()),
	}


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
