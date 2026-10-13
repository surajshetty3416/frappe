# Copyright (c) 2026, Frappe Technologies and contributors
# License: MIT. See LICENSE

"""What a chat makes: web pages, workbooks, dashboards, apps. Each layer names its artifact
DocTypes under the `studio_artifacts` hook, and a Flow Session lists the ones it made or changed
in its `artifacts` table, so Studio can open an artifact beside its chat and a chat beside its
artifact."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, get_fullname

HISTORY_LIMIT = 100


def artifact_types() -> dict[str, dict[str, str]]:
	"""{doctype: {label, route, title_field}} from every layer's `studio_artifacts` hook."""
	# get_hooks merges dict hooks into lists of every app's value; the last one wins
	return {
		doctype: {key: values[-1] for key, values in spec.items()}
		for doctype, spec in frappe.get_hooks("studio_artifacts").items()
	}


def artifact_type(doctype: str) -> dict[str, str]:
	spec = artifact_types().get(doctype)
	if not spec:
		frappe.throw(_("{0} is not a Studio artifact.").format(doctype))
	return spec


def route(doctype: str, name: str) -> str:
	"""The Studio editor's path for one artifact."""
	return artifact_type(doctype)["route"].format(name=name)


def describe(doctype: str, name: str) -> dict[str, str]:
	"""How Studio shows and opens one artifact."""
	title = frappe.db.get_value(doctype, name, artifact_type(doctype)["title_field"])
	return artifact(doctype, name, title)


def artifact(doctype: str, name: str, title: str | None) -> dict[str, str]:
	return {
		"doctype": doctype,
		"name": name,
		"label": artifact_type(doctype)["label"],
		"title": title or name,
		"route": route(doctype, name),
	}


def link(session: str, doctype: str, name: str) -> dict[str, str]:
	"""Record that `session` made or changed the artifact, as its newest, and describe it."""
	doc = frappe.get_doc("Flow Session", session)
	doc.check_permission("write")
	frappe.has_permission(doctype, "read", name, throw=True)
	described = describe(doctype, name)
	doc.add_artifact(doctype, name, described["title"])
	return described


def readable_titles(rows: list[dict]) -> dict[tuple[str, str], str | None]:
	"""Titles of the rows' artifacts the user can still open; deleted or hidden ones are missing."""
	types, titles = artifact_types(), {}
	names = defaultdict(list)
	for row in rows:
		names[row.reference_doctype].append(row.reference_name)
	for doctype, batch in names.items():
		if doctype not in types or not frappe.has_permission(doctype, "read"):
			continue
		title_field = types[doctype]["title_field"]
		docs = frappe.get_list(
			doctype, filters={"name": ("in", batch)}, fields=["name", title_field], limit=len(batch)
		)
		for doc in docs:
			titles[doctype, doc.name] = doc.get(title_field)
	return titles


def artifacts_by_session(rows: list[dict]) -> dict[str, list[dict[str, str]]]:
	"""Each session's artifacts in order, describing only the ones the user can still open."""
	titles = readable_titles(rows)
	found = defaultdict(list)
	for row in rows:
		key = (row.reference_doctype, row.reference_name)
		if key in titles:
			found[row.parent].append(artifact(*key, titles[key]))
	return found


def artifact_rows(sessions: list[str]) -> list[dict]:
	if not sessions:
		return []
	return frappe.get_all(
		"Flow Session Artifact",
		filters={"parenttype": "Flow Session", "parentfield": "artifacts", "parent": ("in", sessions)},
		fields=["parent", "reference_doctype", "reference_name"],
		order_by="idx asc",
	)


def own_chats() -> list[list]:
	"""Filters for the user's own chats with the assistant, as the chat panel lists them. A
	trigger's chats and a test of another agent are not the person's conversations."""
	from frappe.ai.assistant import ASSISTANT_AGENT_TITLE
	from frappe.ai.orchestrator import ORCHESTRATOR_AGENT_TITLE

	return [
		["owner", "=", frappe.session.user],
		# a chat is titled by its first message; one without was never sent
		["title", "is", "set"],
		["source", "!=", "Trigger"],
		["agent", "in", [ASSISTANT_AGENT_TITLE, ORCHESTRATOR_AGENT_TITLE]],
	]


def claim(doc, method: str | None = None) -> None:
	"""doc_events hook: a tool call writes an artifact only when no other chat's running turn
	last edited it, and the write makes its chat the owner. A record of a DocType a chat made is
	data: writing one neither checks nor changes ownership."""
	session = frappe.flags.flow_session
	types = artifact_types()
	if not session or doc.doctype not in types or doc.is_new():
		return
	last = frappe.get_all(
		"Flow Session Artifact",
		filters={
			"parenttype": "Flow Session",
			"parentfield": "artifacts",
			"reference_doctype": doc.doctype,
			"reference_name": doc.name,
		},
		fields=["parent", "creation"],
		order_by="creation desc",
		limit=1,
	)
	last = last[0] if last else None
	if last and last.parent != session:
		other = running_since(last.parent)
		if other and other <= last.creation:
			title = frappe.db.get_value("Flow Session", last.parent, "title") or _("Untitled chat")
			frappe.throw(
				_(
					'{0} {1} is being edited by the chat "{2}" right now. Tell the person to wait for that chat to finish, or to make this change there.'
				).format(types[doc.doctype]["label"], doc.name, title)
			)
	mine = running_since(session)
	if not last or last.parent != session or (mine and last.creation < mine):
		title = frappe.db.get_value(doc.doctype, doc.name, types[doc.doctype]["title_field"])
		frappe.get_doc("Flow Session", session).add_artifact(doc.doctype, doc.name, title or doc.name)


def running_since(session: str):
	"""When the session's running turn started, if one is running."""
	return frappe.db.get_value(
		"Flow Run",
		{"session": session, "status": ("in", ("Running", "Paused"))},
		"creation",
		order_by="creation desc",
	)


@frappe.whitelist()
def link_artifact(session: str, reference_doctype: str, reference_name: str) -> dict[str, str]:
	"""Link an artifact to a chat that worked on it outside a tool, e.g. one opened beside it."""
	return link(session, reference_doctype, reference_name)


@frappe.whitelist()
def get_history(limit: int | str = 20) -> list[dict[str, Any]]:
	"""The user's chats, newest first, each with the artifacts it made (newest last). Activity
	does not reorder them, so a running chat's row stays where the person left it."""
	frappe.has_permission("Flow Session", "read", throw=True)
	sessions = frappe.get_all(
		"Flow Session",
		filters=own_chats(),
		fields=["name", "title", "modified"],
		order_by="creation desc",
		limit=min(cint(limit) or 20, HISTORY_LIMIT),
	)
	found = artifacts_by_session(artifact_rows([session.name for session in sessions]))
	for session in sessions:
		session.artifacts = found[session.name]
	return sessions


@frappe.whitelist()
def get_artifact_session(reference_doctype: str, reference_name: str) -> dict[str, Any] | None:
	"""The user's latest chat that made or changed this artifact, if any."""
	frappe.has_permission("Flow Session", "read", throw=True)
	sessions = frappe.get_all(
		"Flow Session",
		filters=[
			*own_chats(),
			["Flow Session Artifact", "reference_doctype", "=", reference_doctype],
			["Flow Session Artifact", "reference_name", "=", reference_name],
		],
		fields=["name", "title", "modified"],
		order_by="modified desc",
		limit=1,
	)
	return sessions[0] if sessions else None


@frappe.whitelist()
def get_artifact_info(reference_doctype: str, reference_name: str) -> dict[str, Any]:
	"""What the Details drawer says of an artifact: its title, when it was made and changed, and the
	chat that made it, or the person when no chat did."""
	frappe.has_permission(reference_doctype, "read", reference_name, throw=True)
	title_field = artifact_type(reference_doctype)["title_field"]
	doc = frappe.db.get_value(
		reference_doctype, reference_name, [title_field, "owner", "creation", "modified"], as_dict=True
	)
	first = frappe.get_all(
		"Artifact Version",
		filters={"reference_doctype": reference_doctype, "reference_name": reference_name},
		fields=["source", "session"],
		order_by="creation asc",
		limit=1,
	)
	session = first[0].session if first and first[0].source == "Agent" else None
	chat = None
	if session and frappe.has_permission("Flow Session", "read", session):
		chat = {"name": session, "title": frappe.db.get_value("Flow Session", session, "title") or _("Untitled chat")}
	return {
		"title": doc.get(title_field) or reference_name,
		"owner": get_fullname(doc.owner),
		"creation": doc.creation,
		"modified": doc.modified,
		"chat": chat,
	}


@frappe.whitelist()
def get_session_artifacts(session: str) -> list[dict[str, str]]:
	"""What one chat made or changed, newest last."""
	frappe.has_permission("Flow Session", "read", session, throw=True)
	return artifacts_by_session(artifact_rows([session]))[session]


@frappe.whitelist()
def get_run_artifacts(session: str) -> list[dict[str, str]]:
	"""What each of a chat's runs saved, through any tool, last saved last, with the flow server's
	`run_id` of the run, so the run's turn shows a card for it."""
	frappe.has_permission("Flow Session", "read", session, throw=True)
	version, run = frappe.qb.DocType("Artifact Version"), frappe.qb.DocType("Flow Run")
	rows = (
		frappe.qb.from_(version)
		.join(run)
		.on(run.name == version.run)
		.select(version.reference_doctype, version.reference_name, run.daemon_run_id)
		.where((version.session == session) & run.daemon_run_id.isnotnull())
		.orderby(version.modified)
		.run(as_dict=True)
	)
	titles = readable_titles(rows)
	return [
		{**artifact(*key, titles[key]), "run_id": row.daemon_run_id}
		for row in rows
		if (key := (row.reference_doctype, row.reference_name)) in titles
	]
