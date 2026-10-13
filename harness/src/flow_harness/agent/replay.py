"""Replays one recorded assistant message as a run, without a model.

The text streams as the model's would, then each tool call runs as a live call does:
a client tool calls back to the client. A recorded call that never ran (denied,
redirected) is answered with its recorded result instead. The caller sets the pace:
how long the message takes and how long each call stays running.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import AsyncIterator

from flow_harness.agent import loop
from flow_harness.agent.loop import LoopInputs
from flow_harness.events import (
	AnyEvent,
	AssistantMessage,
	RunEnded,
	RunStarted,
	TextDelta,
	ToolCallStarted,
	ToolResult,
	UserMessage,
)
from flow_harness.model.tool_display import tool_call_display_ready_event, with_tool_call_displays

PROVIDER = "replay"


async def step(
	message: UserMessage | None,
	reply: AssistantMessage,
	results: dict[str, ToolResult],
	inputs: LoopInputs,
	seconds: float,
	calls: dict[str, float],
) -> AsyncIterator[AnyEvent]:
	yield RunStarted(run_id=uuid.uuid4().hex[:12])
	if message is not None:
		yield message
	templates = _display_templates(inputs)
	words = _words(reply.text)
	for word in words:
		loop._raise_if_aborted(inputs.abort)
		yield TextDelta(text=word)
		await asyncio.sleep(seconds / len(words))
	if not words:
		await _wait(seconds, inputs)
	for call in reply.tool_calls:
		yield ToolCallStarted(id=call.id, name=call.name)
		ready = tool_call_display_ready_event(
			call.id, call.name, call.arguments, display_template=templates.get(call.name)
		)
		if ready is not None:
			yield ready
	reply = reply.model_copy(
		update={"provider": PROVIDER, "api": PROVIDER, "model": PROVIDER, "seq": None, "parent_seq": None}
	)
	yield with_tool_call_displays(reply, templates)
	tools, ctx = inputs.server_tools or {}, loop._tool_context(inputs)
	for call in reply.tool_calls:
		started = time.monotonic()
		if call.id in results:
			result = results[call.id]
		else:
			result = await loop._run_call(call, False, tools, ctx, inputs)
		await _wait(calls.get(call.id, 0) - (time.monotonic() - started), inputs)
		yield result
	yield RunEnded(reason="done")


async def _wait(seconds: float, inputs: LoopInputs) -> None:
	end = time.monotonic() + seconds
	while (left := end - time.monotonic()) > 0:
		loop._raise_if_aborted(inputs.abort)
		await asyncio.sleep(min(left, 0.2))
	loop._raise_if_aborted(inputs.abort)


def _display_templates(inputs: LoopInputs) -> dict[str, str]:
	templates = {
		tool.name: tool.display_template
		for tool in (inputs.server_tools or {}).values()
		if tool.display_template is not None
	}
	templates.update(loop.client_display_templates(inputs.config.client_tools))
	return templates


def _words(text: str) -> list[str]:
	words = text.split(" ") if text else []
	return [word + (" " if i < len(words) - 1 else "") for i, word in enumerate(words)]
