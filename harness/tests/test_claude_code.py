"""Claude Code as the loop: the `flow` MCP bridge to client tools, Flow's tool names in
the mirror, and the options that keep Claude Code to Flow's tools and prompt. The SDK
client is faked; no `claude` process runs."""

import asyncio
from typing import ClassVar

import pytest
from claude_agent_sdk import AssistantMessage as SDKAssistantMessage
from claude_agent_sdk import ResultMessage, StreamEvent, ToolResultBlock, ToolUseBlock
from claude_agent_sdk import UserMessage as SDKUserMessage
from claude_agent_sdk.types import DeferredToolUse

from flow_harness.agent import claude_code, loop
from flow_harness.events import (
	ApprovalRequired,
	AssistantMessage,
	PendingCall,
	RunEnded,
	ToolCall,
	ToolCallStarted,
	ToolResult,
	UserMessage,
)
from flow_harness.model import ModelRequest
from flow_harness.model.auth import resolve_model_auth
from flow_harness.model.credentials import CredentialStore
from flow_harness.model.providers import claude_code as providers_claude_code
from flow_harness.session.config import SessionConfig
from flow_harness.session.transcript import PendingApproval

CREATE = {
	"type": "function",
	"function": {
		"name": "create",
		"description": "Create a record.",
		"parameters": {
			"type": "object",
			"properties": {"doctype": {"type": "string"}, "doc": {"type": "object"}},
			"required": ["doctype", "doc"],
		},
	},
	"display_template": "Creating {{ doctype }}",
}
READ = {"type": "function", "function": {"name": "read_records", "description": "Read records."}}


def _inputs(tmp_path, **config):
	return loop.LoopInputs(
		config=SessionConfig(
			cwd=str(tmp_path),
			system_prompt="You are Flow.",
			client_tools=[CREATE, READ],
			confirm_tools=["create"],
			callback_url="http://site.localhost/api/method/callback",
			**config,
		),
		messages=[],
		credential_store=CredentialStore(str(tmp_path / "credentials.json")),
		abort=asyncio.Event(),
		model_name="claude-code/opus",
		reasoning_effort="high",
		session_id="s1",
	)


@pytest.fixture
def client_calls(monkeypatch):
	"""Every call the bridge makes back to the client, answered by `answers[mode]`."""
	calls = []
	answers = {"execute": {"content": "created SN-1"}, "confirm": {"prompt": "Create Smoke Note?"}}

	async def fake_call_client(config, session_id, call, *, mode):
		calls.append((mode, session_id, call.name, call.arguments))
		answer = answers[mode]
		if isinstance(answer, Exception):
			raise answer
		return answer

	monkeypatch.setattr(loop, "call_client", fake_call_client)
	return calls, answers


@pytest.fixture
def mcp_tools(monkeypatch):
	"""The tools handed to the `flow` MCP server, by name."""
	served = {}

	def fake_server(name, version="1.0.0", tools=None):
		served.update({tool.name: tool for tool in tools or []})
		return {"type": "sdk", "name": name, "instance": None}

	monkeypatch.setattr(claude_code, "create_sdk_mcp_server", fake_server)
	return served


# --- isolation ---------------------------------------------------------


def test_claude_code_sees_only_flow_tools_and_flows_prompt(tmp_path, mcp_tools):
	options = claude_code._options(_inputs(tmp_path), {}, {})
	assert options.tools == []
	assert options.setting_sources == []
	assert options.strict_mcp_config is True
	assert list(options.mcp_servers) == ["flow"]
	assert options.allowed_tools == ["mcp__flow"]
	assert options.permission_mode == "dontAsk"
	assert options.system_prompt == "You are Flow."
	assert options.verbatim_prompts is True
	assert options.model == "opus"
	assert options.effort == "high"


def test_only_flows_compact_reaches_claude_code_as_a_command(tmp_path, mcp_tools):
	assert claude_code._options(_inputs(tmp_path), {}, {}, command=True).verbatim_prompts is False


def test_a_provider_token_logs_claude_code_in(tmp_path, mcp_tools):
	assert claude_code._options(_inputs(tmp_path), {}, {}).env == {}
	options = claude_code._options(_inputs(tmp_path, api_key="oauth-token"), {}, {})
	assert options.env == {"CLAUDE_CODE_OAUTH_TOKEN": "oauth-token"}


# --- the bridge --------------------------------------------------------


def test_every_client_tool_is_served_with_its_schema(tmp_path, mcp_tools):
	claude_code._flow_server(_inputs(tmp_path))
	assert set(mcp_tools) == {"create", "read_records"}
	assert mcp_tools["create"].input_schema == CREATE["function"]["parameters"]
	assert mcp_tools["read_records"].input_schema == {"type": "object", "properties": {}}


async def test_a_bridged_call_runs_on_the_client(tmp_path, mcp_tools, client_calls):
	calls, _ = client_calls
	claude_code._flow_server(_inputs(tmp_path))
	result = await mcp_tools["create"].handler({"doctype": "DocType", "doc": {"name": "Smoke Note"}})
	assert result == {"content": [{"type": "text", "text": "created SN-1"}], "is_error": False}
	assert calls == [("execute", "s1", "create", {"doctype": "DocType", "doc": {"name": "Smoke Note"}})]


async def test_a_failing_client_call_is_an_error_result(tmp_path, mcp_tools, client_calls):
	_, answers = client_calls
	answers["execute"] = RuntimeError("site down")
	claude_code._flow_server(_inputs(tmp_path))
	result = await mcp_tools["create"].handler({"doctype": "DocType", "doc": {}})
	assert result["is_error"] is True
	assert "site down" in result["content"][0]["text"]


async def test_an_aborted_run_does_not_call_the_client(tmp_path, mcp_tools, client_calls):
	calls, _ = client_calls
	inputs = _inputs(tmp_path)
	inputs.abort.set()
	claude_code._flow_server(inputs)
	result = await mcp_tools["create"].handler({"doctype": "DocType", "doc": {}})
	assert result["is_error"] is True
	assert calls == []


# --- the confirm gate --------------------------------------------------


async def test_a_confirm_tool_is_deferred_with_the_clients_prompt(tmp_path, client_calls):
	calls, _ = client_calls
	prompts = {}
	hook = claude_code._approval_hook(_inputs(tmp_path), {}, prompts)
	output = await hook({"tool_name": "mcp__flow__create", "tool_input": {"doctype": "DocType"}}, "t1", None)
	assert output["hookSpecificOutput"]["permissionDecision"] == "defer"
	assert prompts == {"t1": "Create Smoke Note?"}
	assert calls == [("confirm", "s1", "create", {"doctype": "DocType"})]


async def test_a_free_tool_and_an_approved_call_run(tmp_path, client_calls):
	inputs = _inputs(tmp_path)
	assert (
		await claude_code._approval_hook(inputs, {}, {})({"tool_name": "mcp__flow__read_records"}, "t1", None)
		== {}
	)
	approved = claude_code._approval_hook(inputs, {"t1": "Approve"}, {})
	assert await approved({"tool_name": "mcp__flow__create"}, "t1", None) == {}


async def test_auto_approve_skips_the_gate(tmp_path, client_calls):
	hook = claude_code._approval_hook(_inputs(tmp_path, auto_approve=True), {}, {})
	assert await hook({"tool_name": "mcp__flow__create"}, "t1", None) == {}


async def test_a_denied_call_is_refused_with_the_reason(tmp_path):
	hook = claude_code._approval_hook(_inputs(tmp_path), {"t1": "Deny", "t2": "Name it Smoke"}, {})
	denied = (await hook({"tool_name": "mcp__flow__create"}, "t1", None))["hookSpecificOutput"]
	assert denied["permissionDecision"] == "deny"
	redirected = (await hook({"tool_name": "mcp__flow__create"}, "t2", None))["hookSpecificOutput"]
	assert redirected["permissionDecisionReason"].endswith("Name it Smoke")


# --- Flow's tool names in the mirror -----------------------------------


def _assistant(*blocks, message_id="m1"):
	return SDKAssistantMessage(
		content=list(blocks),
		model="claude-opus",
		message_id=message_id,
		session_id="cc-session",
		uuid=f"u-{message_id}",
		usage={"input_tokens": 10, "output_tokens": 5},
	)


def _result(**fields):
	fields = {"is_error": False, **fields}
	return ResultMessage(
		subtype="success", duration_ms=1, duration_api_ms=1, num_turns=1, session_id="cc", **fields
	)


def test_the_mirror_records_flows_tool_names(tmp_path):
	turn = claude_code._Turn("claude-code/opus", [CREATE], {})
	start = {
		"type": "content_block_start",
		"content_block": {"type": "tool_use", "id": "t1", "name": "mcp__flow__create"},
	}
	started = turn.events(StreamEvent(uuid="e1", session_id="cc", event=start))
	use = ToolUseBlock(id="t1", name="mcp__flow__create", input={"doctype": "DocType"})
	assert turn.events(_assistant(use)) == []
	events = turn.events(SDKUserMessage(content=[ToolResultBlock(tool_use_id="t1", content="created")]))
	assistant = next(e for e in events if isinstance(e, AssistantMessage))
	result = next(e for e in events if isinstance(e, ToolResult))
	assert started == [ToolCallStarted(id="t1", name="create")]
	assert [call.name for call in assistant.tool_calls] == ["create"]
	assert assistant.tool_calls[0].display is not None
	assert (result.name, result.content) == ("create", "created")


def test_a_deferred_call_pauses_under_flows_name_and_prompt(tmp_path):
	turn = claude_code._Turn("claude-code/opus", [CREATE], {"t1": "Create Smoke Note?"})
	turn.events(_assistant(ToolUseBlock(id="t1", name="mcp__flow__create", input={"doctype": "DocType"})))
	deferred = DeferredToolUse(id="t1", name="mcp__flow__create", input={"doctype": "DocType"})
	events = turn.events(_result(deferred_tool_use=deferred))
	approval = next(e for e in events if isinstance(e, ApprovalRequired))
	assert [(c.name, c.prompt) for c in approval.calls] == [("create", "Create Smoke Note?")]
	assert events[-1] == RunEnded(reason="paused")


def test_a_failed_result_ends_the_run_with_claude_codes_reason(tmp_path):
	turn = claude_code._Turn("claude-code/opus", [], {})
	with pytest.raises(RuntimeError, match="Not logged in"):
		turn.events(_result(is_error=True, result="Not logged in · Please run /login"))


# --- a run end to end --------------------------------------------------


class _FakeClient:
	"""Plays back scripted SDK messages, after recording its options and prompt."""

	script: ClassVar[list] = []
	seen: ClassVar[dict] = {}

	def __init__(self, options):
		self.seen["options"] = options

	async def __aenter__(self):
		return self

	async def __aexit__(self, *exc):
		return False

	async def query(self, prompt):
		self.seen["prompt"] = prompt

	async def receive_messages(self):
		for message in self.script:
			yield message


async def test_a_run_mirrors_claude_codes_turns(tmp_path, monkeypatch, mcp_tools):
	monkeypatch.setattr(claude_code, "ClaudeSDKClient", _FakeClient)
	_FakeClient.script = [
		_assistant(ToolUseBlock(id="t1", name="mcp__flow__read_records", input={})),
		SDKUserMessage(content=[ToolResultBlock(tool_use_id="t1", content=[{"type": "text", "text": "[]"}])]),
		_assistant(claude_code.SDKTextBlock(text="No notes yet."), message_id="m2"),
		_result(),
	]
	events = [e async for e in claude_code.run(UserMessage(content="List notes"), _inputs(tmp_path))]
	assert _FakeClient.seen["prompt"] == "List notes"
	assert [e.name for e in events if isinstance(e, ToolResult)] == ["read_records"]
	assert [e.text for e in events if isinstance(e, AssistantMessage) and e.text] == ["No notes yet."]
	assert events[-1] == RunEnded(reason="done")


# --- titles ------------------------------------------------------------


async def test_claude_code_needs_no_stored_credential(tmp_path):
	store = CredentialStore(str(tmp_path / "credentials.json"))
	auth = await resolve_model_auth("claude-code/opus", store)
	assert (auth.api_key, auth.provider_id) == (None, "claude-code")


@pytest.mark.parametrize(("is_error", "stop_reason"), [(False, "stop"), (True, "error")])
async def test_a_title_comes_from_an_isolated_claude_code(monkeypatch, is_error, stop_reason):
	seen = {}

	async def fake_query(prompt, options):
		seen["options"] = options
		yield _assistant(claude_code.SDKTextBlock(text="Smoke Note"))
		yield _result(is_error=is_error)

	monkeypatch.setattr(providers_claude_code, "query", fake_query)
	model = providers_claude_code.ClaudeCodeModel("claude-code/haiku", api_key="oauth-token")
	request = ModelRequest(messages=[UserMessage(content="Title this")], system_prompt="Title it.")
	events = [event async for event in model.run(request)]
	options = seen["options"]
	assert (options.tools, options.setting_sources, options.strict_mcp_config) == ([], [], True)
	assert options.env == {"CLAUDE_CODE_OAUTH_TOKEN": "oauth-token"}
	assert events[0].stop_reason == stop_reason


async def test_a_resumed_call_keeps_its_flow_name(tmp_path, monkeypatch, mcp_tools):
	monkeypatch.setattr(claude_code, "ClaudeSDKClient", _FakeClient)
	_FakeClient.script = [
		SDKUserMessage(content=[ToolResultBlock(tool_use_id="t1", content="created")]),
		_result(),
	]
	inputs = _inputs(tmp_path)
	inputs.messages.append(
		AssistantMessage(content=[ToolCall(id="t1", name="create", arguments={})], stop_reason="tool_use")
	)
	approval = PendingApproval(seq=3, calls=(PendingCall(id="t1", name="create", args={}, prompt="?"),))
	events = [e async for e in claude_code.resume(approval, {"t1": "Approve"}, inputs)]
	assert [(e.name, e.content) for e in events if isinstance(e, ToolResult)] == [("create", "created")]
