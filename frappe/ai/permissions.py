# Copyright (c) 2026, Frappe Technologies and contributors
# License: MIT. See LICENSE

"""Who may use Flow. Three checks, each answering one question:

- Base access: Assistant Users use Flow within their own records; System Managers administer its
  setup. Deliberate Frappe shares may delegate an individual record.
- Doctype permissions: which agents and models. User Permissions narrow them per user; checked
  when a session starts and on every turn.
- Ownership: sessions, runs and personal memories are private to their owner, since a session's
  tools run as them. System Managers also see Trigger sessions.

Triggers run as their run_as account or owner, which must be able to read the agent. The flow
server's callbacks act as the session owner."""

from __future__ import annotations

import frappe

ASSISTANT_USER_ROLE = "Assistant User"


def ensure_assistant_role() -> None:
	"""Create the role on install and migrate."""
	if frappe.db.exists("Role", ASSISTANT_USER_ROLE):
		return
	frappe.get_doc({"doctype": "Role", "role_name": ASSISTANT_USER_ROLE, "desk_access": 1}).insert(
		ignore_permissions=True, ignore_if_duplicate=True
	)


def has_app_permission() -> bool:
	"""Whether the apps screen lists Flow: anyone who may read sessions."""
	return frappe.has_permission("Flow Session", "read")


def check_agent_access(agent: str) -> None:
	"""A public agent is open to anyone, Guest included; any other needs read permission."""
	if not frappe.db.get_value("Flow Agent", agent, "public"):
		frappe.has_permission("Flow Agent", "read", agent, throw=True)


def has_session_permission(doc, user: str) -> bool:
	"""Sessions and runs are private to their owner, except Trigger ones."""
	return user in (doc.owner, "Administrator") or doc.source == "Trigger"


def session_query_conditions(user: str | None = None, doctype: str | None = None) -> str:
	"""The list side of has_session_permission."""
	user = user or frappe.session.user
	if user == "Administrator":
		return ""
	return f"(`tab{doctype}`.`owner` = {frappe.db.escape(user)} or `tab{doctype}`.`source` = 'Trigger')"


def has_memory_permission(doc, user: str) -> bool:
	"""A personal memory is private to its user."""
	return doc.scope != "User" or user in (doc.user, "Administrator")


def memory_query_conditions(user: str | None = None) -> str:
	"""The list side of has_memory_permission."""
	user = user or frappe.session.user
	if user == "Administrator":
		return ""
	user = frappe.db.escape(user)
	return f"(`tabFlow Agent Memory`.`scope` != 'User' or `tabFlow Agent Memory`.`user` = {user})"
