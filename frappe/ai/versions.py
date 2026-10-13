# Copyright (c) 2026, Frappe Technologies and contributors
# License: MIT. See LICENSE

"""Every saved change to an artifact is a version a person can restore. An agent run's saves are
one version, as are a person's saves less than two minutes apart, because editors autosave."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import frappe
from frappe import _
from frappe.model import child_table_fields, default_fields
from frappe.utils import get_fullname, now_datetime

from frappe.ai.artifacts import artifact_types

AUTOSAVE_WINDOW = timedelta(minutes=2)
SKIPPED_FIELDS = {*default_fields, *child_table_fields, "amended_from"}


def record(doc, method: str | None = None) -> None:
	"""doc_events hook: record or extend the artifact's newest version after a save."""
	if doc.doctype not in artifact_types() or frappe.flags.in_install or frappe.flags.in_migrate:
		return
	snapshot = frappe.as_json(doc.as_dict(no_nulls=False, convert_dates_to_str=True), indent=None)
	source = version_source()
	latest = frappe.db.get_value(
		"Artifact Version",
		{"reference_doctype": doc.doctype, "reference_name": doc.name},
		["name", "owner", "source", "run", "modified"],
		order_by="creation desc",
		as_dict=True,
	)
	if latest and extends(latest, source):
		frappe.db.set_value("Artifact Version", latest.name, "snapshot", snapshot)
		return
	frappe.get_doc(
		{
			"doctype": "Artifact Version",
			"reference_doctype": doc.doctype,
			"reference_name": doc.name,
			"snapshot": snapshot,
			**source,
		}
	).insert(ignore_permissions=True)


def delete(doc, method: str | None = None) -> None:
	"""doc_events hook: an artifact's versions go with it."""
	if doc.doctype in artifact_types():
		frappe.db.delete("Artifact Version", {"reference_doctype": doc.doctype, "reference_name": doc.name})


def unlink_sessions(sessions: list[str]) -> None:
	"""Deleted chats leave the versions they made, without a link to them or their runs."""
	version = frappe.qb.DocType("Artifact Version")
	frappe.qb.update(version).set(version.session, None).set(version.run, None).where(
		version.session.isin(sessions)
	).run()


def version_source() -> dict[str, Any]:
	"""Who is saving: the agent run working for the current tool call, else the person."""
	session = frappe.flags.flow_session
	if session:
		return {
			"source": "Agent",
			"session": session,
			"run": frappe.db.get_value("Flow Run", {"session": session}, "name", order_by="creation desc"),
			"label": frappe.db.get_value("Flow Session", session, "title") or _("Assistant"),
		}
	user = get_fullname(frappe.session.user)
	if frappe.flags.restoring_version:
		return {"source": "Person", "label": _("Restored by {0}").format(user)}
	return {"source": "Person", "label": _("Edited by {0}").format(user)}


def extends(latest: dict, source: dict[str, Any]) -> bool:
	if source["source"] == "Agent":
		return latest.source == "Agent" and latest.run == source["run"]
	# a restore is its own undo step
	return (
		not frappe.flags.restoring_version
		and latest.source == "Person"
		and latest.owner == frappe.session.user
		and latest.modified > now_datetime() - AUTOSAVE_WINDOW
	)


@frappe.whitelist()
def get_versions(doctype: str, name: str) -> list[dict[str, Any]]:
	"""The artifact's versions, newest first."""
	frappe.has_permission(doctype, "read", name, throw=True)
	return frappe.get_all(
		"Artifact Version",
		filters={"reference_doctype": doctype, "reference_name": name},
		fields=["name", "creation", "owner", "source", "label"],
		order_by="creation desc",
	)


@frappe.whitelist()
def restore_version(version: str) -> dict[str, Any]:
	"""Put the artifact back as it was in `version`; the save records a new version."""
	ref = frappe.db.get_value(
		"Artifact Version", version, ["reference_doctype", "reference_name", "snapshot"], as_dict=True
	)
	if not ref:
		frappe.throw(_("Version {0} not found.").format(version), frappe.DoesNotExistError)
	doc = frappe.get_doc(ref.reference_doctype, ref.reference_name)
	doc.check_permission("write")
	doc.update(fields(frappe.parse_json(ref.snapshot), doc))
	frappe.flags.restoring_version = True
	try:
		doc.save()
	finally:
		frappe.flags.restoring_version = False
	return doc.as_dict()


def fields(snapshot: dict, doc) -> dict[str, Any]:
	"""The snapshot's values, without the document's identity and with child rows as new rows."""
	tables = {df.fieldname for df in doc.meta.get_table_fields()}
	values = {}
	for key, value in snapshot.items():
		if key in SKIPPED_FIELDS or key.startswith("_"):
			continue
		if key in tables:
			value = [{k: v for k, v in row.items() if k not in SKIPPED_FIELDS} for row in value or []]
		values[key] = value
	return values
