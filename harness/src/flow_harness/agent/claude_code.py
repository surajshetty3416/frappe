"""Runs a turn on Claude Code through the Claude Agent SDK, for `claude-code/*` models.

Claude Code owns the loop, its tools and the conversation. It runs as the unmodified
`claude` binary under the user's own login, so a Claude subscription works and Flow
never holds a Claude credential. Flow's log mirrors what Claude Code did as ordinary
events, and each Flow session resumes one Claude Code session with a derived id.
"""

from __future__ import annotations

import base64
import json
import uuid
from collections.abc import AsyncIterator
from typing import Any, cast

from claude_agent_sdk import (
	TERMINAL_TASK_STATUSES,
	ClaudeAgentOptions,
	ClaudeSDKClient,
	EffortLevel,
	HookCallback,
	HookJSONOutput,
	HookMatcher,
	ResultMessage,
	StreamEvent,
	TaskNotificationMessage,
	TaskStartedMessage,
	TaskUpdatedMessage,
	get_session_messages,
)
from claude_agent_sdk import AssistantMessage as SDKAssistantMessage
from claude_agent_sdk import TextBlock as SDKTextBlock
from claude_agent_sdk import ThinkingBlock as SDKThinkingBlock
from claude_agent_sdk import ToolResultBlock as SDKToolResultBlock
from claude_agent_sdk import ToolUseBlock as SDKToolUseBlock
from claude_agent_sdk import UserMessage as SDKUserMessage
from claude_agent_sdk.types import SystemPromptPreset

from flow_harness.agent.loop import LoopInputs
from flow_harness.events import (
	AnyEvent,
	ApprovalRequired,
	AssistantContent,
	AssistantMessage,
	PendingCall,
	ReasoningEffort,
	RunEnded,
	RunStarted,
	TextContent,
	TextDelta,
	ThinkingContent,
	ThinkingDelta,
	ToolCall,
	ToolCallStarted,
	ToolResult,
	Usage,
	UserMessage,
)
from flow_harness.model.cancellation import iterate_with_cancellation
from flow_harness.model.content import resolve_user_content
from flow_harness.model.tool_display import with_tool_call_displays
from flow_harness.session.transcript import PendingApproval

PREFIX = "claude-code"
API = "claude-agent-sdk"
_EFFORT: dict[ReasoningEffort, EffortLevel] = {
	"minimal": "low",
	"low": "low",
	"medium": "medium",
	"high": "high",
	"xhigh": "xhigh",
	"max": "max",
}


# Claude Code's tools, worded like Flow's own so both render alike
_DISPLAY_TEMPLATES = {
	"Bash": "Running command {{ command }}",
	"Read": "Reading file {{ file_path }}",
	"Write": "Writing file {{ file_path }}",
	"Edit": "Editing file {{ file_path }}",
	"MultiEdit": "Editing file {{ file_path }}",
	"NotebookEdit": "Editing notebook {{ notebook_path }}",
	"Grep": "Searching code for {{ pattern }}",
	"Glob": "Finding files {{ pattern }}",
	"Task": "Sub-agent: {{ description }}",
	"Agent": "Sub-agent: {{ description }}",
	"WebFetch": "Fetching {{ url }}",
	"WebSearch": "Searching the web for {{ query }}",
	"TodoWrite": "Updating todos",
}
_context_windows: dict[str, int] = {}
# Claude Code's tools that do what a Flow built-in does; one the session leaves out, by
# its own choice or the daemon's policy, is withheld from Claude Code too
_FLOW_EQUIVALENTS = {
	"bash": ("Bash", "BashOutput", "KillShell", "Monitor"),
	"write": ("Write", "NotebookEdit"),
	"edit": ("Edit", "MultiEdit", "NotebookEdit"),
	"read": ("Read",),
}
_GATED_TOOLS = frozenset({"Bash", "Edit", "MultiEdit", "Write", "NotebookEdit", "WebFetch"})


def is_claude_code(model_name: str) -> bool:
	return model_name.split("/", 1)[0] == PREFIX


async def run(message: UserMessage, inputs: LoopInputs) -> AsyncIterator[AnyEvent]:
	yield RunStarted(run_id=uuid.uuid4().hex[:12])
	yield message
	async for event in _turns(inputs, _prompt(message, inputs), {}):
		yield event


async def resume(
	approval: PendingApproval, answers: dict[str, str], inputs: LoopInputs
) -> AsyncIterator[AnyEvent]:
	"""Resuming the session re-runs the deferred call through the hook, which now
	answers it: "Approve" runs it, anything else is refused with the reason."""
	yield RunStarted(run_id=uuid.uuid4().hex[:12])
	async for event in _turns(inputs, None, {call.id: answers[call.id] for call in approval.calls}):
		yield event


async def compact(instructions: str | None, inputs: LoopInputs) -> AsyncIterator[AnyEvent]:
	"""Claude Code compacts its own conversation; Flow's log keeps the full mirror."""
	yield RunStarted(run_id=uuid.uuid4().hex[:12])
	async for event in _turns(inputs, f"/compact {instructions or ''}".strip(), {}):
		yield event


async def _turns(
	inputs: LoopInputs, prompt: str | AsyncIterator[dict[str, Any]] | None, answers: dict[str, str]
) -> AsyncIterator[AnyEvent]:
	"""One Flow run lasts until Claude Code is idle: a result that leaves background
	tasks running is followed by another turn once they report back."""
	turn = _Agents(inputs.model_name)
	tasks: set[str] = set()
	async with ClaudeSDKClient(_options(inputs, answers)) as client:
		await client.query(prompt if prompt is not None else _nothing())
		async for sdk_message in iterate_with_cancellation(client.receive_messages(), inputs.abort):
			if isinstance(sdk_message, TaskStartedMessage):
				tasks.add(sdk_message.task_id)
			elif isinstance(sdk_message, TaskNotificationMessage) or (
				isinstance(sdk_message, TaskUpdatedMessage) and sdk_message.status in TERMINAL_TASK_STATUSES
			):
				tasks.discard(sdk_message.task_id)
			events = turn.events(sdk_message)
			if isinstance(sdk_message, ResultMessage) and tasks:
				events = [event for event in events if not isinstance(event, RunEnded)]
			for event in events:
				yield event
			if isinstance(sdk_message, ResultMessage) and not tasks:
				return
			for steering in _drain(inputs):
				yield steering
				await client.query(_prompt(steering, inputs))


def _prompt(message: UserMessage, inputs: LoopInputs) -> str | AsyncIterator[dict[str, Any]]:
	"""Text attachments are inlined into the text; images go as image blocks."""
	text, images = resolve_user_content(message, resolve_attachment=inputs.resolve_attachment)
	if not images:
		return text
	content: list[dict[str, Any]] = [{"type": "text", "text": text}] if text else []
	for image in images:
		source = {
			"type": "base64",
			"media_type": image.mime_type,
			"data": base64.b64encode(image.data).decode(),
		}
		content.append({"type": "image", "source": source})
	return _stream(
		{"type": "user", "message": {"role": "user", "content": content}, "parent_tool_use_id": None}
	)


async def _stream(*messages: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
	for message in messages:
		yield message


async def _nothing() -> AsyncIterator[dict[str, Any]]:
	return
	yield


def _approval_hook(inputs: LoopInputs, answers: dict[str, str]) -> HookCallback:
	async def hook(hook_input: Any, tool_use_id: str | None, context: Any) -> HookJSONOutput:
		answer = answers.get(tool_use_id or "")
		if answer == "Approve" or (
			answer is None and not _needs_confirmation(inputs, hook_input["tool_name"])
		):
			return {}
		if answer is None:
			decision, reason = "defer", None
		elif answer == "Deny":
			decision, reason = "deny", "The user denied this tool call."
		else:
			decision, reason = "deny", f"The user wants changes before this runs: {answer}"
		output: dict[str, Any] = {"hookEventName": "PreToolUse", "permissionDecision": decision}
		if reason:
			output["permissionDecisionReason"] = reason
		return cast(HookJSONOutput, {"hookSpecificOutput": output})

	return hook


def _needs_confirmation(inputs: LoopInputs, tool_name: str) -> bool:
	if (inputs.approval_config or inputs.config).auto_approve:
		return False
	return tool_name in _GATED_TOOLS or tool_name in inputs.config.confirm_tools


def _options(inputs: LoopInputs, answers: dict[str, str]) -> ClaudeAgentOptions:
	config = inputs.config
	anchor = _anchor(inputs)
	system_prompt = SystemPromptPreset(type="preset", preset="claude_code")
	if config.system_append:
		system_prompt["append"] = config.system_append
	return ClaudeAgentOptions(
		model=inputs.model_name.partition("/")[2] or None,
		cwd=config.cwd,
		system_prompt=system_prompt,
		setting_sources=["user", "project", "local"],
		permission_mode="bypassPermissions",
		hooks={"PreToolUse": [HookMatcher(hooks=[_approval_hook(inputs, answers)])]},
		disallowed_tools=_withheld_tools(inputs),
		include_partial_messages=True,
		forward_subagent_text=True,
		max_turns=config.max_turns,
		effort=_EFFORT.get(inputs.reasoning_effort) if inputs.reasoning_effort else None,
		**_resume_options(anchor, config.cwd),
	)


def _withheld_tools(inputs: LoopInputs) -> list[str]:
	enabled = inputs.server_tools or {}
	return sorted(
		{name for tool, names in _FLOW_EQUIVALENTS.items() if tool not in enabled for name in names}
	)


def _anchor(inputs: LoopInputs) -> dict[str, str] | None:
	"""Where Claude Code's conversation stands on Flow's active branch: the session and
	entry of the last Claude Code message, recorded on its last content block."""
	for message in reversed(inputs.messages):
		if isinstance(message, AssistantMessage) and message.provider == PREFIX and message.content:
			state = message.content[-1].provider_state or {}
			if "claude_session" in state:
				return state
	return None


def _resume_options(anchor: dict[str, str] | None, cwd: str) -> dict[str, Any]:
	"""Resume the anchored session; fork it at the anchor when Flow rewound past later
	entries, so the old branch stays intact in both logs. An anchor gone from the active
	chain sits behind a compaction, which a rewind cannot cross."""
	if anchor is None:
		return {}
	session_id, entry = anchor["claude_session"], anchor["claude_uuid"]
	latest = [m.uuid for m in get_session_messages(session_id, directory=cwd) if m.type == "assistant"]
	if entry not in latest or latest[-1] == entry:
		return {"resume": session_id}
	return {"resume": session_id, "resume_session_at": entry, "fork_session": True}


def _drain(inputs: LoopInputs) -> list[UserMessage]:
	if inputs.next_steering is None:
		return []
	return list(iter(inputs.next_steering, None))


class _Agents:
	"""One `_Turn` per agent: Claude Code's sub-agents report under the id of the `Task`
	call that started them, which is what Flow tags a sub-agent's events with."""

	def __init__(self, model_name: str) -> None:
		self.model_name = model_name
		self.turns: dict[str | None, _Turn] = {}

	def events(self, message: object) -> list[AnyEvent]:
		if isinstance(message, ResultMessage):
			children = [
				e for key, turn in self.turns.items() if key is not None for e in _tagged(turn._flush(), key)
			]
			return children + self._turn(None).events(message)
		parent = getattr(message, "parent_tool_use_id", None)
		return _tagged(self._turn(parent).events(message), parent)

	def _turn(self, parent: str | None) -> _Turn:
		return self.turns.setdefault(parent, _Turn(self.model_name))


def _tagged(events: list[AnyEvent], subagent_id: str | None) -> list[AnyEvent]:
	if subagent_id is None:
		return events
	return [event.model_copy(update={"subagent_id": subagent_id}) for event in events]


class _Turn:
	"""Folds the SDK's per-block assistant messages back into one Flow message per API
	response, and names tool results after the call they answer."""

	def __init__(self, model_name: str) -> None:
		self.model_name = model_name
		self.message_id: str | None = None
		self.content: list[AssistantContent] = []
		self.usage: dict[str, Any] | None = None
		self.tool_names: dict[str, str] = {}
		self.entry: dict[str, str] = {}

	def events(self, message: object) -> list[AnyEvent]:
		if isinstance(message, StreamEvent):
			return self._delta(message)
		if isinstance(message, SDKAssistantMessage):
			events = self._flush() if message.message_id != self.message_id else []
			self.message_id = message.message_id
			self.usage = message.usage
			self.entry = {"claude_session": message.session_id or "", "claude_uuid": message.uuid or ""}
			self.content.extend(item for block in message.content if (item := _content(block)) is not None)
			for block in message.content:
				if isinstance(block, SDKToolUseBlock):
					self.tool_names[block.id] = block.name
			return events
		if isinstance(message, SDKUserMessage):
			if isinstance(message.content, str):
				return []
			return self._flush() + [
				self._tool_result(block) for block in message.content if isinstance(block, SDKToolResultBlock)
			]
		if isinstance(message, ResultMessage):
			events = self._flush()
			for usage in (message.model_usage or {}).values():
				if usage.get("contextWindow"):
					_context_windows[self.model_name] = usage["contextWindow"]
			if message.is_error and message.subtype != "success":
				raise RuntimeError(
					"; ".join(message.errors or []) or f"Claude Code ended with {message.subtype}"
				)
			if message.is_error:
				raise RuntimeError(message.result or "Claude Code request failed")
			if message.deferred_tool_use is not None:
				call = message.deferred_tool_use
				prompt = f"Approve `{call.name}`?\n\n" + json.dumps(call.input, indent=2, default=str)
				pending = PendingCall(id=call.id, name=call.name, args=call.input, prompt=prompt)
				return [*events, ApprovalRequired(calls=[pending]), RunEnded(reason="paused")]
			reason = "max_turns" if message.subtype == "error_max_turns" else "done"
			return [*events, RunEnded(reason=reason)]
		return []

	def _delta(self, message: StreamEvent) -> list[AnyEvent]:
		event = message.event
		if event.get("type") == "content_block_start":
			block = event.get("content_block", {})
			if block.get("type") == "tool_use":
				return [ToolCallStarted(id=block["id"], name=block["name"])]
		if event.get("type") == "content_block_delta":
			delta = event.get("delta", {})
			if delta.get("type") == "text_delta":
				return [TextDelta(text=delta["text"])]
			if delta.get("type") == "thinking_delta":
				return [ThinkingDelta(thinking=delta["thinking"])]
		return []

	def _flush(self) -> list[AnyEvent]:
		if self.message_id is None:
			return []
		calls = any(isinstance(block, ToolCall) for block in self.content)
		if self.content and self.entry["claude_uuid"]:
			self.content[-1] = self.content[-1].model_copy(update={"provider_state": self.entry})
		assistant = AssistantMessage(
			content=self.content,
			api=API,
			provider=PREFIX,
			model=self.model_name,
			response_id=self.message_id,
			stop_reason="tool_use" if calls else "stop",
		)
		events: list[AnyEvent] = [with_tool_call_displays(assistant, _DISPLAY_TEMPLATES)]
		if self.usage:
			events.append(_usage(self.usage).model_copy(update={"context_window": self._context_window()}))
		self.message_id, self.content, self.usage = None, [], None
		return events

	def _context_window(self) -> int:
		# learned from the last run's result; a first run guesses from the alias
		return _context_windows.get(self.model_name) or (1_000_000 if "[1m]" in self.model_name else 200_000)

	def _tool_result(self, block: SDKToolResultBlock) -> ToolResult:
		return ToolResult(
			tool_call_id=block.tool_use_id,
			name=self.tool_names.get(block.tool_use_id, "unknown"),
			content=_text(block.content),
			is_error=bool(block.is_error),
		)


def _content(block: object) -> AssistantContent | None:
	if isinstance(block, SDKTextBlock):
		return TextContent(text=block.text)
	if isinstance(block, SDKThinkingBlock):
		return ThinkingContent(thinking=block.thinking, thinking_signature=block.signature)
	if isinstance(block, SDKToolUseBlock):
		return ToolCall(id=block.id, name=block.name, arguments=block.input)
	return None


def _text(content: str | list[dict[str, Any]] | None) -> str:
	if content is None or isinstance(content, str):
		return content or ""
	return "\n".join(item.get("text", "") for item in content if item.get("type") == "text")


def _usage(usage: dict[str, Any]) -> Usage:
	cache_read = usage.get("cache_read_input_tokens") or 0
	cache_write = usage.get("cache_creation_input_tokens") or 0
	return Usage(
		input_tokens=(usage.get("input_tokens") or 0) + cache_read + cache_write,
		output_tokens=usage.get("output_tokens") or 0,
		cache_read_tokens=cache_read,
		cache_write_tokens=cache_write,
	)
