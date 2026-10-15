# Copyright (c) 2026, Frappe Technologies and contributors
# License: MIT. See LICENSE

"""Orchestrate mode: a chat whose agent builds nothing. It sends each task to the chat that owns
the artifacts involved, or to a new chat, as the person. A routed turn is a Flow Run of that chat
whose reference is the orchestrator's session; once the last one ends, the orchestrator gets
their results in one message and sums them up."""

from __future__ import annotations

import json

import frappe
from frappe import _
from frappe.utils.synchronization import filelock

from frappe.ai.assistant import ASSISTANT_AGENT_TITLE
from frappe.ai.lib.agent import Agent
from frappe.ai.lib.session import ENDED, new_session
from frappe.ai.lib.tool import ToolContext, tool

ORCHESTRATOR_AGENT_TITLE = "Orchestrator"
TASK_ENDED = "frappe.ai.orchestrator.task_ended"
REPORT_TAG = "task_results"
REPORT_NOTICE = "All routed tasks finished."
CHAT_LIMIT = 30
TITLE_LIMIT = 140
REPLY_LIMIT = 600
OPEN = ("Running", "Paused")

INSTRUCTIONS = (
	"You route work in Studio for {{ full_name }}. You never build or change anything yourself: "
	"chats with the builder assistant do the work, and you send it to them as the person.\n\n"
	"For each request, call list_chats first. Split the request into tasks that can run on their "
	"own. A task that changes an artifact a chat owns, or adds records to a DocType a chat owns, "
	"goes to that chat with send_to_chat. Every other task goes to a new chat with start_chat, even "
	"when it only reads another chat's artifact. Tasks that depend on each other go together, in "
	"one message to one chat. Send every task in the same turn, as parallel tool calls.\n\n"
	"A message is a complete instruction: the chat cannot see this conversation. Keep the person's "
	"words and name artifacts exactly. A title is 2 to 5 words.\n\n"
	"After routing, reply in one sentence of at most 8 words, such as \"Sent 3 tasks to their chats.\" "
	"A card under your reply already shows each task, so never name or describe them. "
	"A message with <task_results> means every task "
	"has ended: say what was made or changed in at most two sentences, and name any task that "
	"failed. No lists."
)


def agents() -> list[Agent]:
	"""`flow_agents` hook: the Orchestrator, on the Assistant's model."""
	model = frappe.db.get_value("Flow Agent", ASSISTANT_AGENT_TITLE, "model")
	if not model:
		return []
	return [
		Agent(
			name=ORCHESTRATOR_AGENT_TITLE,
			model=model,
			reasoning_effort="low",
			description="Sends each task to the chat that owns its artifacts, or to a new chat.",
			instructions=INSTRUCTIONS,
			tools=[list_chats, start_chat, send_to_chat],
			max_iterations=20,
		)
	]


def sync() -> None:
	for agent in agents():
		agent.sync()


@tool
def list_chats(*, ctx: ToolContext) -> list[dict]:
	"""The person's chats with the builder assistant in this project, newest first: `chat` id,
	`title`, whether a turn is `running`, and the artifacts it `owns`, the ones it changed last. A
	DocType's records belong to the chat that owns the DocType."""
	project = frappe.db.get_value("Flow Session", ctx.session_id, "project")
	sessions = frappe.get_all(
		"Flow Session",
		filters=builder_chats(ctx.user, project),
		fields=["name", "title"],
		order_by="modified desc",
		limit=CHAT_LIMIT,
	)
	names = [session.name for session in sessions]
	busy = set(
		frappe.get_all("Flow Run", filters={"session": ("in", names), "status": ("in", OPEN)}, pluck="session")
		if names
		else []
	)
	owned = owned_artifacts(names)
	return [
		{
			"chat": session.name,
			"title": session.title,
			"running": session.name in busy,
			"owns": owned.get(session.name, []),
		}
		for session in sessions
	]


@tool
def start_chat(title: str, message: str, *, ctx: ToolContext) -> dict:
	"""Start a new chat with the builder assistant and send it `message`, its first message."""
	orchestrator = frappe.get_doc("Flow Session", ctx.session_id)
	doc = new_session(
		ASSISTANT_AGENT_TITLE,
		title=title.strip()[:TITLE_LIMIT] or None,
		auto_approve=bool(orchestrator.auto_approve),
		project=orchestrator.project,
	)
	return routed(doc, message, send(doc, message, orchestrator.name))


@tool
def send_to_chat(chat: str, message: str, *, ctx: ToolContext) -> dict:
	"""Send `message` to one of the person's chats from list_chats. When that chat is running, the
	message waits and goes once its turn ends."""
	doc = frappe.get_doc("Flow Session", chat)
	project = frappe.db.get_value("Flow Session", ctx.session_id, "project")
	if doc.owner != ctx.user or doc.agent != ASSISTANT_AGENT_TITLE or doc.project != project:
		frappe.throw(_("{0} is not one of the person's chats with the builder assistant.").format(chat))
	if hold(doc.name, message, ctx.session_id):
		return routed(doc, message, None)
	return routed(doc, message, send(doc, message, ctx.session_id))


def builder_chats(user: str, project: str | None = None) -> list[list]:
	filters = [
		["owner", "=", user],
		["title", "is", "set"],
		["source", "!=", "Trigger"],
		["agent", "=", ASSISTANT_AGENT_TITLE],
	]
	if project:
		filters.append(["project", "=", project])
	return filters


def owned_artifacts(sessions: list[str]) -> dict[str, list[dict]]:
	"""Each session's artifacts that no later chat changed, as `claim` decides ownership."""
	if not sessions:
		return {}
	rows = frappe.get_all(
		"Flow Session Artifact",
		filters={"parenttype": "Flow Session", "parentfield": "artifacts", "parent": ("in", sessions)},
		fields=["parent", "reference_doctype", "reference_name", "title", "creation"],
		order_by="creation asc",
	)
	last = {(row.reference_doctype, row.reference_name): row for row in rows}
	owned = {}
	for (doctype, name), row in last.items():
		newer = frappe.db.exists(
			"Flow Session Artifact",
			{
				"parenttype": "Flow Session",
				"reference_doctype": doctype,
				"reference_name": name,
				"creation": (">", row.creation),
			},
		)
		if not newer:
			owned.setdefault(row.parent, []).append({"doctype": doctype, "name": name, "title": row.title or name})
	return owned


def send(doc, message: str, orchestrator: str):
	run = doc.chat(
		message, on_complete=TASK_ENDED, reference_doctype="Flow Session", reference_name=orchestrator
	)
	# the chat's own callbacks are other requests, and need its rows now
	frappe.db.commit()
	return run


def routed(doc, message: str, run) -> dict:
	return {
		"routed": {
			"chat": doc.name,
			"title": doc.title,
			"message": message,
			"run": run.name if run else None,
			"status": "Running" if run else "Queued",
		}
	}


# A message for a running chat waits in Redis until that chat's turn ends, as a queued message
# waits in the composer. The running turn's on_complete sends it.
def queue_key(chat: str) -> str:
	return f"flow_orchestrator_queue|{chat}"


def routed_key(orchestrator: str) -> str:
	return f"flow_orchestrator_queued_chats|{orchestrator}"


def hold(chat: str, message: str, orchestrator: str) -> bool:
	"""Queue `message` when the chat runs a turn whose end can send it; False when it is idle."""
	active = frappe.db.get_value(
		"Flow Run",
		{"session": chat, "status": ("in", OPEN)},
		["name", "on_complete"],
		as_dict=True,
		order_by="creation desc",
		for_update=True,
	)
	if not active:
		return False
	if active.on_complete and active.on_complete != TASK_ENDED:
		return False  # a run keeps its first on_complete; this one steers in instead
	if not active.on_complete:
		frappe.db.set_value("Flow Run", active.name, "on_complete", TASK_ENDED, update_modified=False)
	frappe.cache.rpush(queue_key(chat), json.dumps({"orchestrator": orchestrator, "message": message}))
	frappe.cache.rpush(routed_key(orchestrator), chat)
	frappe.db.commit()
	return True


def queued(chat: str) -> list[dict]:
	return [json.loads(item) for item in frappe.cache.lrange(queue_key(chat), 0, -1)]


def waiting_for(orchestrator: str) -> bool:
	return bool(queued_for(orchestrator))


def queued_for(orchestrator: str) -> list[dict]:
	chats = {chat.decode() for chat in frappe.cache.lrange(routed_key(orchestrator), 0, -1)}
	return [item for chat in chats for item in queued(chat) if item["orchestrator"] == orchestrator]


def progress(orchestrator: str) -> dict[str, int] | None:
	"""How many of the tasks routed since the last report have ended, of how many; None when there are none."""
	seen = reported(orchestrator)
	runs = frappe.get_all(
		"Flow Run",
		filters={"reference_doctype": "Flow Session", "reference_name": orchestrator},
		fields=["name", "status"],
	)
	runs = [run for run in runs if run.name not in seen]
	total = len(runs) + len(queued_for(orchestrator))
	if not total:
		return None
	return {"done": sum(run.status in ENDED for run in runs), "total": total}


def task_ended(run) -> None:
	"""on_complete of a routed turn, or of a turn a routed message waited on."""
	item = frappe.cache.lpop(queue_key(run.session))
	if item:
		item = json.loads(item)
		send_next(run.session, item["message"], item["orchestrator"])
	if run.reference_doctype == "Flow Session" and run.reference_name:
		# after commit, so a task that ended at the same moment reads as ended
		frappe.enqueue(
			"frappe.ai.orchestrator.report", orchestrator=run.reference_name, enqueue_after_commit=True
		)


def send_next(chat: str, message: str, orchestrator: str) -> None:
	doc = frappe.get_doc("Flow Session", chat)
	doc.chat(message, on_complete=TASK_ENDED, reference_doctype="Flow Session", reference_name=orchestrator)


def report(orchestrator: str) -> None:
	"""Once none of the orchestrator's tasks runs or waits, send it the results it has not seen."""
	with filelock(f"flow_orchestrator_{orchestrator}", timeout=60):
		runs = frappe.get_all(
			"Flow Run",
			filters={"reference_doctype": "Flow Session", "reference_name": orchestrator},
			fields=["name", "session", "status", "error"],
			order_by="creation asc",
		)
		if any(run.status in OPEN for run in runs) or waiting_for(orchestrator):
			return
		seen = reported(orchestrator)
		new = [run for run in runs if run.name not in seen and run.status in ENDED]
		if not new:
			return
		results = [
			{
				"run": run.name,
				"chat": run.session,
				"title": frappe.db.get_value("Flow Session", run.session, "title"),
				"status": run.status,
				"reply": (last_reply(run.name) or run.error or "")[:REPLY_LIMIT],
			}
			for run in new
		]
		frappe.get_doc("Flow Session", orchestrator).chat(
			f"{REPORT_NOTICE}\n\n<{REPORT_TAG}>\n{json.dumps(results)}\n</{REPORT_TAG}>"
		)
		frappe.db.commit()


def reported(orchestrator: str) -> set[str]:
	"""Runs an earlier result message named."""
	seen = set()
	for text in frappe.get_all(
		"Flow Run",
		filters={"session": orchestrator, "input": ("like", f"%<{REPORT_TAG}>%")},
		pluck="input",
	):
		body = text.split(f"<{REPORT_TAG}>", 1)[1].split(f"</{REPORT_TAG}>", 1)[0]
		seen.update(item["run"] for item in json.loads(body))
	return seen


def last_reply(run: str) -> str | None:
	return frappe.db.get_value(
		"Flow Session Message", {"run": run, "role": "assistant", "content": ("is", "set")}, "content",
		order_by="idx desc",
	)


@frappe.whitelist()
def get_task(session: str, chat: str, message: str, run: str | None = None) -> dict:
	"""A routed task's status: Queued, Running, Paused, Completed, Denied or Failed."""
	frappe.has_permission("Flow Session", "read", session, throw=True)
	frappe.has_permission("Flow Session", "read", chat, throw=True)
	if not run:
		run = frappe.db.get_value(
			"Flow Run",
			{"session": chat, "reference_doctype": "Flow Session", "reference_name": session, "input": message},
			"name",
			order_by="creation desc",
		)
	if run:
		return {"run": run, "status": frappe.db.get_value("Flow Run", run, "status")}
	waiting = any(item["orchestrator"] == session and item["message"] == message for item in queued(chat))
	return {"run": None, "status": "Queued" if waiting else "Failed"}
