# Copyright (c) 2026, Frappe Technologies and contributors
# License: MIT. See LICENSE

"""Recorded chats, played back without a model. A recording is a chat's log, exported as
JSON from one site and imported on another. A replay plays it into a new chat one step at
a time, a step being one assistant message: the flow server streams its text and runs its
tool calls through the site's tool callback, as in a live run. The site names the documents
a replay makes afresh, so each step's new results are read beside the recorded ones, and a
recorded value that came back different is replaced in every later step. At any point the
chat continues live through the usual `frappe.ai.api.run`."""

from __future__ import annotations

import json
import re
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint

from frappe.ai.daemon.client import DaemonClient, DaemonError
from frappe.ai.lib.session import _default_agent_name, flow_server, new_session

FORMAT = "flow-recording"
NEVER_RAN = {
	"denied",
	"redirect",
	"aborted",
	"truncated",
	"blocked",
}  # statuses of calls the loop answered itself
BLOCK_KEYS = {
	"text": ("type", "text"),
	"thinking": ("type", "thinking", "thinking_signature", "redacted"),
	"tool_call": ("type", "id", "name", "arguments", "error"),
}
ON_COMPLETE = "frappe.ai.replay.settle_run"
NAME_LIMIT = 140  # a Data field's length


@frappe.whitelist()
def export_session(session: str) -> dict[str, Any]:
	"""A chat as a recording: its messages in order, with each tool call's arguments and
	result, the artifacts it linked and its agent."""
	doc = frappe.get_doc("Flow Session", session)
	doc.check_permission("read")
	messages = []
	for row in doc.entries(path="active")["entries"]:
		if row.get("subagent_id"):
			continue
		if row["type"] == "user_message":
			messages.append({"type": "user_message", "content": _text(row["content"])})
		elif row["type"] == "assistant_message":
			content = [
				{key: block[key] for key in BLOCK_KEYS[block["type"]] if key in block}
				for block in row.get("content") or []
				if block.get("type") in BLOCK_KEYS
			]
			messages.append({"type": "assistant_message", "content": content})
		elif row["type"] == "tool_result":
			messages.append(
				{key: row.get(key) for key in ("type", "tool_call_id", "name", "content", "is_error")}
			)
	return {
		"format": FORMAT,
		"title": doc.title,
		"agent": doc.agent,
		"site": frappe.local.site,
		"messages": messages,
		"artifacts": [
			{"doctype": row.reference_doctype, "name": row.reference_name, "title": row.title}
			for row in doc.artifacts
		],
	}


@frappe.whitelist()
def import_recording(recording: str | dict, position: int | str | None = None) -> dict[str, Any]:
	"""Keep an exported chat on this site as a recording, last in the list unless `position`
	says otherwise."""
	frappe.has_permission("Flow Recording", "create", throw=True)
	data = frappe.parse_json(recording) if isinstance(recording, str) else recording
	if not isinstance(data, dict) or data.get("format") != FORMAT:
		frappe.throw(_("This is not an exported chat."), title=_("Invalid Recording"))
	agent = data.get("agent")
	doc = frappe.get_doc(
		{
			"doctype": "Flow Recording",
			"title": data.get("title"),
			"position": cint(position) or _last_position() + 1,
			"agent": agent if agent and frappe.db.exists("Flow Agent", agent) else _default_agent_name(),
			"source_site": data.get("site"),
			"steps": len(steps(data["messages"])),
			"data": json.dumps(data),
		}
	).insert()
	return {"name": doc.name, "title": doc.title, "position": doc.position, "agent": doc.agent, "steps": doc.steps}


@frappe.whitelist()
def list_recordings() -> list[dict[str, Any]]:
	return frappe.get_list(
		"Flow Recording",
		fields=["name", "title", "position", "agent", "steps", "source_site", "creation"],
		order_by="position asc, creation asc",
	)


@frappe.whitelist()
def start_replay(recording: str) -> dict[str, Any]:
	"""A new chat of the current user's, ready to play `recording` from its first step."""
	rec = frappe.get_doc("Flow Recording", recording)
	rec.check_permission("read")
	frappe.has_permission("Flow Session", "create", throw=True)
	session = new_session(rec.agent, title=rec.title)
	replay = frappe.get_doc(
		{"doctype": "Flow Replay", "session": session.name, "recording": rec.name, "names": "{}"}
	).insert()
	frappe.db.commit()
	return state(replay)


@frappe.whitelist()
def get_replay(session: str) -> dict[str, Any] | None:
	"""The chat's replay, or None for a chat that is not one."""
	frappe.has_permission("Flow Session", "read", session, throw=True)
	if not frappe.db.exists("Flow Replay", session):
		return None
	replay = frappe.get_doc("Flow Replay", session)
	settle(replay)
	return state(replay)


@frappe.whitelist()
def play_step(session: str, delay: float | str | None = None) -> dict[str, Any]:
	"""Play the next step and answer at once; the step's run ends like a live one, with a
	run_ended event. `delay` is the seconds between streamed words."""
	replay = _load(session, "write")
	settle(replay)
	if replay.status == "Playing":
		frappe.throw(_("The previous step is still playing."), title=_("Replay Busy"))
	if replay.status == "Done":
		frappe.throw(_("This replay has played every step."), title=_("Replay Ended"))
	if replay.status == "Failed":
		frappe.throw(
			_("This replay stopped at a failed step: {0}").format(replay.error), title=_("Replay Ended")
		)
	if went_live(replay):
		frappe.throw(_("This chat went live, so its replay has ended."), title=_("Replay Ended"))

	step = recording_steps(replay.recording)[replay.step]
	names = json.loads(replay.names or "{}")
	message = mapped(step["message"], names)
	reply = mapped(step["reply"], names)
	results = [mapped(result, names) for result in step["results"] if never_ran(result, step["reply"])]

	with flow_server() as client:
		from_seq = client.get_session(session)["latest_seq"]
	# one run per recorded turn, as live: its tool calls version an artifact once
	if message or not replay.run:
		run = frappe.get_doc(
			{"doctype": "Flow Run", "session": session, "source": "Manual", "status": "Running"}
		).insert(ignore_permissions=True)
	else:
		# the chat's sync may still be recording the previous step's end on this run
		run = frappe.get_doc("Flow Run", replay.run, for_update=True)
		run.update({"status": "Running", "error": None})
	run.on_complete = ON_COMPLETE
	run.save(ignore_permissions=True)
	replay.update({"status": "Playing", "run": run.name, "from_seq": from_seq, "error": None})
	replay.save()
	frappe.db.commit()  # the flow server's callbacks are other requests
	try:
		with DaemonClient.for_site() as client:
			client.replay(session, reply, message=message, results=results, delay=_delay(delay))
	except DaemonError as exc:
		run.reload()
		run.update({"status": "Failed", "error": str(exc), "on_complete": None})
		run.save(ignore_permissions=True)
		replay.db_set({"status": "Ready", "error": str(exc)})
		frappe.db.commit()
		frappe.throw(str(exc), title=_("Flow Server"))
	return state(replay)


def settle_run(run) -> None:
	"""Flow Run on_complete: record what the step's run did."""
	if frappe.db.exists("Flow Replay", run.session):
		settle(frappe.get_doc("Flow Replay", run.session))


def settle(replay) -> None:
	"""Once the playing step's run has ended, learn the names it got and stop on a call that
	failed where the recording's succeeded."""
	if replay.status != "Playing":
		return
	session = frappe.get_doc("Flow Session", replay.session)
	rows = [
		row
		for row in session.entries(since=replay.from_seq, path="all")["entries"]
		if not row.get("subagent_id")
	]
	if not any(row["type"] == "run_ended" for row in rows):
		return
	replay.reload()  # a concurrent settle may have won
	if replay.status != "Playing":
		return
	new = {row["tool_call_id"]: row for row in rows if row["type"] == "tool_result"}
	errors = [row["message"] for row in rows if row["type"] == "run_error"]
	names = json.loads(replay.names or "{}")
	recording = recording_steps(replay.recording)
	for recorded in recording[replay.step]["results"]:
		result = new.get(recorded["tool_call_id"])
		if result is None:
			errors.append(_("{0} returned no result.").format(recorded["name"]))
		elif result.get("is_error") and not recorded.get("is_error"):
			errors.append(f"{recorded['name']}: {result['content']}")
		elif not result.get("is_error"):
			learn(_json(recorded["content"]), _json(result["content"]), names)
	step = replay.step + 1
	status = "Failed" if errors else "Done" if step >= len(recording) else "Ready"
	replay.update(
		{
			"step": step,
			"status": status,
			"error": "\n".join(errors)[:2000] or None,
			"names": json.dumps(names),
		}
	)
	replay.save(ignore_permissions=True)


def state(replay) -> dict[str, Any]:
	recording = frappe.db.get_value("Flow Recording", replay.recording, ["title", "steps"], as_dict=True)
	return {
		"session": replay.session,
		"recording": replay.recording,
		"title": recording.title,
		"step": replay.step,
		"steps": recording.steps,
		"status": replay.status,
		"error": replay.error,
		"names": json.loads(replay.names or "{}"),
		"live": went_live(replay),
	}


def went_live(replay) -> bool:
	"""A run the replay did not start is a live message, which ends the replay."""
	latest = frappe.db.get_value("Flow Run", {"session": replay.session}, "name", order_by="creation desc")
	return bool(latest and latest != replay.run)


# --- steps ----------------------------------------------------------------


def recording_steps(recording: str) -> list[dict[str, Any]]:
	data = frappe.parse_json(frappe.db.get_value("Flow Recording", recording, "data"))
	return steps(data["messages"])


def steps(messages: list[dict]) -> list[dict[str, Any]]:
	"""One step per assistant message, with the user messages before it and the results of
	its calls."""
	found, waiting = [], []
	for message in messages:
		if message["type"] == "user_message":
			waiting.append(message["content"])
		elif message["type"] == "assistant_message":
			reply = {"content": message["content"]}
			found.append({"message": "\n\n".join(waiting) or None, "reply": reply, "results": []})
			waiting = []
		elif message["type"] == "tool_result" and found:
			found[-1]["results"].append(message)
	return found


def never_ran(result: dict, reply: dict) -> bool:
	"""A recorded call the loop answered itself (a denial, a malformed call) is answered
	with its recorded result again, not run."""
	if not result.get("is_error"):
		return False
	call = next((b for b in reply["content"] if b.get("id") == result["tool_call_id"]), {})
	if call.get("error"):
		return True
	content = _json(result.get("content"))
	return isinstance(content, dict) and content.get("status") in NEVER_RAN


# --- names ----------------------------------------------------------------


def learn(recorded: Any, new: Any, names: dict[str, str]) -> None:
	"""Walk a recorded result beside its replayed one; a name-like value that differs at
	the same path maps to the new one. Values with a digit only: document names and routes
	carry one, while a different word (a status, a label) is not a rename, and a name is one
	short line, while a changed text (a skill, a message) is not a rename either."""
	if isinstance(recorded, dict) and isinstance(new, dict):
		for key in recorded.keys() & new.keys():
			learn(recorded[key], new[key], names)
	elif isinstance(recorded, list) and isinstance(new, list):
		for old_item, new_item in zip(recorded, new, strict=False):
			learn(old_item, new_item, names)
	elif isinstance(recorded, str) and isinstance(new, str):
		if (
			4 <= len(recorded) <= NAME_LIMIT
			and "\n" not in recorded
			and any(c.isdigit() for c in recorded)
			and mapped(recorded, names) != new
		):
			names[recorded] = new


def mapped(value: Any, names: dict[str, str]) -> Any:
	"""`value` with every recorded name replaced by its new one, inside strings too."""
	if not names:
		return value
	pattern = re.compile(
		r"(?<![A-Za-z0-9_])("
		+ "|".join(re.escape(old) for old in sorted(names, key=len, reverse=True))
		+ r")(?![A-Za-z0-9_])"
	)
	return _replace(value, pattern, names)


def _replace(value: Any, pattern: re.Pattern, names: dict[str, str]) -> Any:
	if isinstance(value, str):
		return pattern.sub(lambda match: names[match.group(1)], value)
	if isinstance(value, dict):
		return {key: _replace(item, pattern, names) for key, item in value.items()}
	if isinstance(value, list):
		return [_replace(item, pattern, names) for item in value]
	return value


# --- helpers --------------------------------------------------------------


def _load(session: str, ptype: str):
	doc = frappe.get_doc("Flow Session", session)
	doc.check_permission(ptype)
	if not frappe.db.exists("Flow Replay", session):
		frappe.throw(_("This chat is not a replay."), title=_("Not a Replay"))
	return frappe.get_doc("Flow Replay", session)


def _last_position() -> int:
	last = frappe.get_all("Flow Recording", fields=["position"], order_by="position desc", limit=1)
	return cint(last[0].position) if last else 0


def _text(content: str | list[dict]) -> str:
	if isinstance(content, str):
		return content
	return "".join(block.get("text", "") for block in content if block.get("type") == "text")


def _json(value: Any) -> Any:
	if not isinstance(value, str):
		return value
	try:
		return json.loads(value)
	except ValueError:
		return value


def _delay(delay: float | str | None) -> float | None:
	return None if delay in (None, "") else float(delay)
