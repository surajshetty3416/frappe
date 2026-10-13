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
from frappe.utils import cint, flt

from frappe.ai.daemon.client import DaemonClient, DaemonError
from frappe.ai.lib.session import _default_agent_name, new_session

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

# Pace, in seconds at 1x: a step keeps the recorded time of its message and of each call,
# divided by the speed. A recording without times takes these per word and per call.
SPEED = 4
WORD_SECONDS = 0.12
CALL_SECONDS = 1.6
MESSAGE_CEILING = 20.0
CALL_CEILING = 6.0
FLOOR = 0.4  # at any speed, so a tool row never flashes by


@frappe.whitelist()
def export_session(session: str) -> dict[str, Any]:
	"""A chat as a recording: its messages in order, with each tool call's arguments and
	result, the artifacts it linked, its agent and approval mode. An assistant message and
	a tool result keep the seconds they took, from the row before them."""
	doc = frappe.get_doc("Flow Session", session)
	doc.check_permission("read")
	messages, last = [], None
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
		else:
			continue
		if messages[-1]["type"] != "user_message" and last and row.get("ts"):
			messages[-1]["seconds"] = round(row["ts"] - last, 2)
		last = row.get("ts")
	return {
		"format": FORMAT,
		"title": doc.title,
		"agent": doc.agent,
		"auto_approve": bool(doc.auto_approve),
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
	auto_approve = frappe.parse_json(rec.data).get("auto_approve")
	session = new_session(rec.agent, title=rec.title, auto_approve=bool(auto_approve))
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
def play_step(session: str, speed: float | str | None = None) -> dict[str, Any]:
	"""Play the next step and answer at once; the step's run ends like a live one, with a
	run_ended event. `speed` divides the recorded times."""
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

	recording = recording_steps(replay.recording)
	step = recording[replay.step]
	names = json.loads(replay.names or "{}")
	message = mapped(step["message"], names)
	reply = mapped(step["reply"], names)
	answered = answered_calls(recording[: replay.step + 1], replay_tools(replay.session))
	results = [mapped(result, names) for result in step["results"] if result["tool_call_id"] in answered]
	seconds, calls = pace(step, flt(speed) or SPEED)

	# the step starts before its run opens, as in chat(), so a sync that sees the run open
	# finds the flow server running it, or its end in the log
	try:
		with DaemonClient.for_site() as client:
			from_seq = client.get_session(session)["latest_seq"]
			client.replay(session, reply, message=message, results=results, seconds=seconds, calls=calls)
	except DaemonError as exc:
		replay.db_set("error", str(exc))
		frappe.db.commit()
		frappe.throw(str(exc), title=_("Flow Server"))
	# one run per recorded turn, as live: its tool calls version an artifact once
	if message or not replay.run:
		run = frappe.get_doc(
			{"doctype": "Flow Run", "session": session, "source": "Manual", "status": "Running"}
		)
	else:
		run = frappe.get_doc("Flow Run", replay.run)
		run.update({"status": "Running", "error": None})
	run.on_complete = ON_COMPLETE
	run.save(ignore_permissions=True)
	replay.update({"status": "Playing", "run": run.name, "from_seq": from_seq, "error": None})
	replay.save()
	frappe.db.commit()  # the flow server's callbacks are other requests
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
	# the end the sync recorded, so the next step's rows never share a sync with this one's
	run = frappe.db.get_value("Flow Run", replay.run, ["status", "error"], as_dict=True)
	if run.status == "Running":
		return
	session = frappe.get_doc("Flow Session", replay.session)
	rows = [
		row
		for row in session.entries(since=replay.from_seq, path="all")["entries"]
		if not row.get("subagent_id")
	]
	# the poll, the run's on_complete and play_step settle concurrently: one holds the row,
	# the others then read what it saved
	replay.flags.for_update = True
	replay.reload()
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
		"message": first_message(replay.recording) if not replay.step else None,
		"step": replay.step,
		"steps": recording.steps,
		"status": replay.status,
		"error": replay.error,
		"names": json.loads(replay.names or "{}"),
		"live": went_live(replay),
	}


def first_message(recording: str) -> str | None:
	"""What the person said first, which a replay not yet played shows."""
	found = recording_steps(recording)
	return found[0]["message"] if found else None


def went_live(replay) -> bool:
	"""A run the replay did not start is a live message, which ends the replay."""
	latest = frappe.db.get_value("Flow Run", {"session": replay.session}, "name", order_by="creation desc")
	return bool(latest and latest != replay.run)


# --- steps ----------------------------------------------------------------


def recording_steps(recording: str) -> list[dict[str, Any]]:
	data = frappe.parse_json(frappe.db.get_value("Flow Recording", recording, "data"))
	return steps(data["messages"])


def steps(messages: list[dict]) -> list[dict[str, Any]]:
	"""One step per assistant message, with the user messages before it, the results of its
	calls and the recorded seconds of the message and of each call."""
	found, waiting = [], []
	for message in messages:
		if message["type"] == "user_message":
			waiting.append(message["content"])
		elif message["type"] == "assistant_message":
			found.append(
				{
					"message": "\n\n".join(waiting) or None,
					"reply": {"content": message["content"]},
					"results": [],
					"seconds": message.get("seconds"),
					"calls": {},
				}
			)
			waiting = []
		elif message["type"] == "tool_result" and found:
			result = {key: value for key, value in message.items() if key != "seconds"}
			found[-1]["results"].append(result)
			if message.get("seconds") is not None:
				found[-1]["calls"][result["tool_call_id"]] = message["seconds"]
	return found


def pace(step: dict, speed: float) -> tuple[float, dict[str, float]]:
	"""The seconds the step's message takes and each of its calls stays running."""
	content = step["reply"]["content"]
	seconds = step["seconds"]
	if seconds is None:
		words = sum(len(block["text"].split()) for block in content if block.get("type") == "text")
		seconds = words * WORD_SECONDS
	calls = {
		block["id"]: max(min(step["calls"].get(block["id"], CALL_SECONDS), CALL_CEILING) / speed, FLOOR)
		for block in content
		if block.get("type") == "tool_call"
	}
	return max(min(seconds, MESSAGE_CEILING) / speed, FLOOR), calls


def replay_tools(session: str) -> set[str]:
	"""The session's agent's tools that a replay answers from their recording."""
	agent = frappe.db.get_value("Flow Session", session, "agent")
	return {
		tool.name
		for tool in frappe.get_doc("Flow Agent", agent).client_tools(session)
		if tool.replay_from_recording
	}


def answered_calls(played: list[dict], tools: set[str]) -> set[str]:
	"""The calls of the last of `played` steps that are answered with their recorded result,
	not run: a call the loop answered itself, a call to one of `tools`, and a call naming what
	only such a recorded result gave, since that name exists on the recording's site alone."""
	recorded_only: set[str] = set()
	answered: set[str] = set()
	for step in played:
		answered = set()
		calls = {block["id"]: block for block in step["reply"]["content"] if block.get("type") == "tool_call"}
		for result in step["results"]:
			arguments = _json(calls.get(result["tool_call_id"], {}).get("arguments"))
			if never_ran(result, step["reply"]):
				answered.add(result["tool_call_id"])
			elif result["name"] in tools or _mentions(arguments, recorded_only):
				answered.add(result["tool_call_id"])
				if not result.get("is_error"):
					recorded_only |= _names(_json(result["content"])) - _names(arguments)
	return answered


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
		if _name_like(recorded) and mapped(recorded, names) != new:
			names[recorded] = new


def _name_like(value: str) -> bool:
	return 4 <= len(value) <= NAME_LIMIT and "\n" not in value and any(c.isdigit() for c in value)


def _names(value: Any) -> set[str]:
	"""The name-like values anywhere in `value`."""
	if isinstance(value, dict):
		return set().union(*map(_names, value.values()))
	if isinstance(value, list):
		return set().union(*map(_names, value))
	return {value} if isinstance(value, str) and _name_like(value) else set()


def mapped(value: Any, names: dict[str, str]) -> Any:
	"""`value` with every recorded name replaced by its new one, inside strings too."""
	if not names:
		return value
	return _replace(value, _pattern(names), names)


def _mentions(value: Any, names: set[str]) -> bool:
	return bool(names) and bool(_pattern(names).search(json.dumps(value)))


def _pattern(names) -> re.Pattern:
	return re.compile(
		r"(?<![A-Za-z0-9_])("
		+ "|".join(re.escape(old) for old in sorted(names, key=len, reverse=True))
		+ r")(?![A-Za-z0-9_])"
	)


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
