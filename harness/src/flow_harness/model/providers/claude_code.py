"""Claude Code as a plain model, for Flow's one-shot calls such as session titles.

Runs go through `flow_harness.agent.claude_code`, where Claude Code owns the loop. This
adapter answers one tool-less request over a flattened transcript.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from claude_agent_sdk import AssistantMessage as SDKAssistantMessage
from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, TextBlock, query

from flow_harness.events import AnyEvent, AssistantMessage, TextContent, ToolResult, Usage, UserMessage
from flow_harness.model.base import Model, ModelRequest
from flow_harness.model.cancellation import iterate_with_cancellation

# Claude Code's own aliases, which follow its latest models
MODELS = ("opus", "sonnet", "haiku", "opus[1m]", "sonnet[1m]")


class ClaudeCodeModel(Model):
	api = "claude-agent-sdk"
	provider = "claude-code"

	def __init__(self, name: str, *, api_key: str | None = None, **_: object) -> None:
		self.name = name
		self.model = name.partition("/")[2]
		self.api_key = api_key

	async def run(self, request: ModelRequest) -> AsyncIterator[AnyEvent]:
		options = ClaudeAgentOptions(
			model=self.model or None,
			system_prompt=request.system_prompt,
			tools=[],
			setting_sources=[],
			strict_mcp_config=True,
			max_turns=1,
			verbatim_prompts=True,
			env={"CLAUDE_CODE_OAUTH_TOKEN": self.api_key} if self.api_key else {},
		)
		text: list[str] = []
		usage = Usage()
		failed = False
		async for message in iterate_with_cancellation(
			query(prompt=_prompt(request), options=options), request.cancellation
		):
			if isinstance(message, SDKAssistantMessage):
				text.extend(block.text for block in message.content if isinstance(block, TextBlock))
			elif isinstance(message, ResultMessage):
				failed = message.is_error
				usage = Usage(
					input_tokens=(message.usage or {}).get("input_tokens") or 0,
					output_tokens=(message.usage or {}).get("output_tokens") or 0,
				)
		yield AssistantMessage(
			content=[TextContent(text="".join(text))],
			api=self.api,
			provider=self.provider,
			model=self.name,
			stop_reason="error" if failed else "stop",
		)
		yield usage


def _prompt(request: ModelRequest) -> str:
	if len(request.messages) == 1 and isinstance(request.messages[0], UserMessage):
		return request.messages[0].text
	lines = []
	for message in request.messages:
		if isinstance(message, UserMessage):
			lines.append(f"User: {message.text}")
		elif isinstance(message, AssistantMessage):
			lines.append(f"Assistant: {message.text}")
		elif isinstance(message, ToolResult):
			lines.append(f"Tool result ({message.name}): {message.content}")
	return "\n\n".join(lines)
