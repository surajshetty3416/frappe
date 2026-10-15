# Copyright (c) 2026, Frappe Technologies and contributors
# License: MIT. See LICENSE

"""A Studio project gathers what one piece of work needs: its chats, the artifacts they made, and the
skills, knowledge bases and context its chats start with. A Flow Session names its project, and the
project lists every artifact its chats made, so they outlive the chats."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import frappe
from frappe.ai.artifacts import HISTORY_LIMIT, artifact, artifact_types, own_chats
from frappe.ai.doctype.flow_skill.flow_skill import skill_command
from frappe.ai.orchestrator import OPEN, ORCHESTRATOR_AGENT_TITLE, progress

ARTIFACT_LIMIT = 200


@frappe.whitelist()
def get_projects() -> list[dict[str, Any]]:
	"""The projects the user can open, the one worked on last first."""
	return frappe.get_list(
		"Studio Project",
		fields=["name", "title", "description", "modified"],
		order_by="modified desc",
		limit=0,
	)


@frappe.whitelist()
def get_project(project: str) -> dict[str, Any]:
	"""The project, what its chats made and the skills they use, as its page shows them."""
	doc = frappe.get_doc("Studio Project", project)
	doc.check_permission("read")
	return {
		"project": {
			"name": doc.name,
			"title": doc.title,
			"description": doc.description,
			"modified": doc.modified,
			"can_write": bool(doc.has_permission("write")),
		},
		"artifacts": artifacts(doc),
		"skills": skills(doc),
	}


@frappe.whitelist()
def get_artifacts(doctypes: list[str] | str, project: str | None = None) -> list[dict[str, Any]]:
	"""The artifacts of `doctypes` the user can open, or only those `project`'s chats made, the
	latest changed first, each with the project that made it."""
	doctypes = frappe.parse_json(doctypes)
	if project:
		doc = frappe.get_doc("Studio Project", project)
		doc.check_permission("read")
		names = {doctype: batch for doctype, batch in made_names(doc).items() if doctype in doctypes}
	else:
		names = dict.fromkeys(doctypes)
	return with_projects(latest(names, ARTIFACT_LIMIT))


@frappe.whitelist()
def get_running_chats(project: str) -> list[dict[str, Any]]:
	"""The user's chats in `project` that run, wait for approval, or wait for the tasks they routed,
	the newest first. `tasks` counts an orchestrator's routed tasks that ended, of all of them."""
	frappe.has_permission("Studio Project", "read", project, throw=True)
	sessions = frappe.get_all(
		"Flow Session",
		filters=[*own_chats(), ["project", "=", project]],
		fields=["name", "title", "modified", "agent"],
		order_by="creation desc",
		limit=HISTORY_LIMIT,
	)
	if not sessions:
		return []
	open_runs = dict(
		frappe.get_all(
			"Flow Run",
			filters={"session": ("in", [row.name for row in sessions]), "status": ("in", OPEN)},
			fields=["session", "status"],
			order_by="creation asc",
			as_list=True,
		)
	)
	running = []
	for row in sessions:
		tasks = progress(row.name) if row.agent == ORCHESTRATOR_AGENT_TITLE else None
		routing = tasks and tasks["done"] < tasks["total"]
		if row.name not in open_runs and not routing:
			continue
		running.append(
			{
				"name": row.name,
				"title": row.title,
				"modified": row.modified,
				"status": open_runs.get(row.name, "Running"),
				"tasks": tasks,
			}
		)
	return running


def artifacts(doc) -> list[dict[str, Any]]:
	"""What the project's chats made that the user can still open, the latest changed first."""
	return latest(made_names(doc))


def made_names(doc) -> dict[str, list[str]]:
	names = defaultdict(list)
	for row in doc.artifacts:
		names[row.reference_doctype].append(row.reference_name)
	return names


def latest(names: dict[str, list[str] | None], limit: int | None = None) -> list[dict[str, Any]]:
	"""The named records of each artifact DocType the user can read, or all of them when its names
	are None, the latest changed first."""
	types = artifact_types()
	found = []
	for doctype, batch in names.items():
		if doctype not in types or not frappe.has_permission(doctype, "read"):
			continue
		title_field = types[doctype]["title_field"]
		for record in frappe.get_list(
			doctype,
			filters={"name": ("in", batch)} if batch is not None else {},
			fields=["name", title_field, "modified"],
			order_by="modified desc",
			limit=len(batch) if batch is not None else limit,
		):
			found.append(
				{**artifact(doctype, record.name, record.get(title_field)), "modified": record.modified}
			)
	found.sort(key=lambda row: row["modified"], reverse=True)
	return found[:limit] if limit else found


def with_projects(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
	"""Each row with the first project the user can open whose chats made it, or None."""
	if not rows:
		return rows
	readable = {row.name: row.title for row in get_projects()}
	made_in = {}
	for link in frappe.get_all(
		"Studio Project Artifact",
		filters={"parenttype": "Studio Project", "reference_name": ("in", [row["name"] for row in rows])},
		fields=["parent", "reference_doctype", "reference_name"],
	):
		if link.parent in readable:
			made_in.setdefault((link.reference_doctype, link.reference_name), link.parent)
	for row in rows:
		project = made_in.get((row["doctype"], row["name"]))
		row["project"] = {"name": project, "title": readable[project]} if project else None
	return rows


def skills(doc) -> list[dict[str, Any]]:
	"""The project's own skills, then the enabled global ones every chat can load."""
	own = [row.skill for row in doc.skills]
	fields = ["name", "title", "description", "enabled", "is_global", "user_invocable"]
	rows = frappe.get_all("Flow Skill", filters={"name": ("in", own)}, fields=fields, order_by="title")
	rows += frappe.get_all(
		"Flow Skill",
		filters={"is_global": 1, "enabled": 1, "name": ("not in", own)},
		fields=fields,
		order_by="title",
	)
	for row in rows:
		row.own = row.name in own
		row.command = skill_command(row.name) if row.user_invocable else None
	return rows

