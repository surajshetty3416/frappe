"""Runs a turn on Claude Code through the Claude Agent SDK, for `claude-code/*` models.

Claude Code owns the loop and the conversation; Flow owns the tools. Claude Code's own
tools, settings, skills and MCP servers are all off: it sees only the session's client
tools, served in process as the `flow` MCP server, and Flow's system prompt. It runs
under the daemon user's Claude login.
Flow's log mirrors what Claude Code did as ordinary events, under Flow's tool names, and
each Flow session resumes one Claude Code session.
"""

from __future__ import annotations

import base64
import json
import uuid
from collections.abc import AsyncIterator
from typing import Any, cast

from claude_agent_sdk import AssistantMessage as SDKAssistantMessage
from claude_agent_sdk import (
	ClaudeAgentOptions,
	ClaudeSDKClient,
	EffortLevel,
	HookCallback,
	HookJSONOutput,
	HookMatcher,
	McpSdkServerConfig,
	ResultMessage,
	SdkMcpTool,
	StreamEvent,
	ToolAnnotations,
	create_sdk_mcp_server,
	get_session_messages,
)
from claude_agent_sdk import TextBlock as SDKTextBlock
from claude_agent_sdk import ThinkingBlock as SDKThinkingBlock
from claude_agent_sdk import ToolResultBlock as SDKToolResultBlock
from claude_agent_sdk import ToolUseBlock as SDKToolUseBlock
from claude_agent_sdk import UserMessage as SDKUserMessage

from flow_harness.agent import loop
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
from flow_harness.model.cancellation import ModelCancelled, iterate_with_cancellation
from flow_harness.model.content import resolve_user_content
from flow_harness.model.tool_display import with_tool_call_displays
from flow_harness.session.transcript import PendingApproval
from flow_harness.tools.builtins.common import DEFAULT_MAX_BYTES

PREFIX = "claude-code"
API = "claude-agent-sdk"
MCP_SERVER = "flow"
# how Claude Code names a tool of the `flow` MCP server
TOOL_PREFIX = f"mcp__{MCP_SERVER}__"
_EFFORT: dict[ReasoningEffort, EffortLevel] = {
	"minimal": "low",
	"low": "low",
	"medium": "medium",
	"high": "high",
	"xhigh": "xhigh",
	"max": "max",
}
_context_windows: dict[str, int] = {}


def is_claude_code(model_name: str) -> bool:
	return model_name.split("/", 1)[0] == PREFIX


def flow_tool_name(name: str) -> str:
	return name.removeprefix(TOOL_PREFIX)


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
	async for event in _turns(inputs, f"/compact {instructions or ''}".strip(), {}, command=True):
		yield event


async def _turns(
	inputs: LoopInputs,
	prompt: str | AsyncIterator[dict[str, Any]] | None,
	answers: dict[str, str],
	*,
	command: bool = False,
) -> AsyncIterator[AnyEvent]:
	"""One Flow run lasts until Claude Code returns a result."""
	prompts: dict[str, str] = {}
	turn = _Turn(inputs.model_name, inputs.config.client_tools, prompts)
	async with ClaudeSDKClient(_options(inputs, answers, prompts, command=command)) as client:
		await client.query(prompt if prompt is not None else _nothing())
		async for sdk_message in iterate_with_cancellation(client.receive_messages(), inputs.abort):
			for event in turn.events(sdk_message):
				yield event
			if isinstance(sdk_message, ResultMessage):
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


def _options(
	inputs: LoopInputs, answers: dict[str, str], prompts: dict[str, str], *, command: bool = False
) -> ClaudeAgentOptions:
	config = inputs.config
	return ClaudeAgentOptions(
		model=inputs.model_name.partition("/")[2] or None,
		cwd=config.cwd,
		system_prompt=config.system_prompt or "",
		tools=[],
		setting_sources=[],
		strict_mcp_config=True,
		mcp_servers={MCP_SERVER: _flow_server(inputs)},
		allowed_tools=[f"mcp__{MCP_SERVER}"],
		permission_mode="dontAsk",
		hooks={"PreToolUse": [HookMatcher(hooks=[_approval_hook(inputs, answers, prompts)])]},
		# a user's "@/path" or "/command" stays text; only Flow's own /compact is a command
		verbatim_prompts=not command,
		include_partial_messages=True,
		max_turns=config.max_turns,
		effort=_EFFORT.get(inputs.reasoning_effort) if inputs.reasoning_effort else None,
		**_resume_options(_anchor(inputs), config.cwd),
	)


def _flow_server(inputs: LoopInputs) -> McpSdkServerConfig:
	"""The session's client tools, each calling back to the client like the native loop."""
	tools = []
	for client_tool in inputs.config.client_tools:
		function = client_tool["function"]
		tools.append(
			SdkMcpTool(
				name=function["name"],
				description=function.get("description") or "",
				input_schema=function.get("parameters") or {"type": "object", "properties": {}},
				handler=_client_tool_handler(inputs, function["name"]),
				# results are capped to this already; past it Claude Code would park them in a file
				annotations=ToolAnnotations(maxResultSizeChars=2 * DEFAULT_MAX_BYTES),
			)
		)
	return create_sdk_mcp_server(MCP_SERVER, tools=tools)


def _client_tool_handler(inputs: LoopInputs, name: str):
	async def handler(args: dict[str, Any]) -> dict[str, Any]:
		call = ToolCall(id=uuid.uuid4().hex, name=name, arguments=args)
		try:
			result = await loop._finished_call(call, {}, loop._tool_context(inputs), inputs)
		except ModelCancelled:
			return {"content": [{"type": "text", "text": loop._ABORTED}], "is_error": True}
		return {"content": [{"type": "text", "text": result.content}], "is_error": result.is_error}

	return handler


def _approval_hook(inputs: LoopInputs, answers: dict[str, str], prompts: dict[str, str]) -> HookCallback:
	async def hook(hook_input: Any, tool_use_id: str | None, context: Any) -> HookJSONOutput:
		name = flow_tool_name(hook_input["tool_name"])
		answer = answers.get(tool_use_id or "")
		if answer == "Approve" or (answer is None and not loop._needs_confirmation(inputs, name, {})):
			return {}
		if answer is None:
			call = ToolCall(id=tool_use_id or "", name=name, arguments=hook_input.get("tool_input") or {})
			prompts[call.id] = await loop._confirmation_prompt(call, {}, inputs)
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


class _Turn:
	"""Folds the SDK's per-block assistant messages back into one Flow message per API
	response, and names tool calls and results by Flow's tool names."""

	def __init__(self, model_name: str, client_tools: list[dict], prompts: dict[str, str]) -> None:
		self.model_name = model_name
		self.display_templates = loop.client_display_templates(client_tools)
		self.prompts = prompts
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
					self.tool_names[block.id] = flow_tool_name(block.name)
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
				name = flow_tool_name(call.name)
				prompt = self.prompts.get(call.id) or (
					f"Approve `{name}`?\n\n" + json.dumps(call.input, indent=2, default=str)
				)
				pending = PendingCall(id=call.id, name=name, args=call.input, prompt=prompt)
				return [*events, ApprovalRequired(calls=[pending]), RunEnded(reason="paused")]
			reason = "max_turns" if message.subtype == "error_max_turns" else "done"
			return [*events, RunEnded(reason=reason)]
		return []

	def _delta(self, message: StreamEvent) -> list[AnyEvent]:
		event = message.event
		if event.get("type") == "content_block_start":
			block = event.get("content_block", {})
			if block.get("type") == "tool_use":
				return [ToolCallStarted(id=block["id"], name=flow_tool_name(block["name"]))]
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
		events: list[AnyEvent] = [with_tool_call_displays(assistant, self.display_templates)]
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
		return ToolCall(id=block.id, name=flow_tool_name(block.name), arguments=block.input)
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
