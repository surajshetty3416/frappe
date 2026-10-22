# Copyright (c) 2026, Frappe Technologies and contributors
# License: MIT. See LICENSE

"""Model credentials for the flow server."""

from __future__ import annotations

import time
from contextlib import suppress
from typing import Any

import frappe
from frappe import _
from frappe.ai.daemon.client import DaemonClient, DaemonError

PING_TIMEOUT = 30

# runs on Claude Code in the daemon, not through litellm
CLAUDE_CODE = "claude-code"
CLAUDE_CODE_MODEL = "Claude Code Opus"


def model_config(model: str, *, check_permission: bool = True) -> dict[str, Any]:
	"""The daemon's model, api_key, api_base and model_params for a Flow Model the user may use."""
	if check_permission and not frappe.has_permission("Flow Model", "read", model):
		frappe.throw(
			_("You don't have permission to use {0}. Use a different model instead.").format(model),
			frappe.PermissionError,
			title=_("Model Not Permitted"),
		)
	doc = frappe.get_doc("Flow Model", model)
	if not doc.enabled:
		frappe.throw(_("Flow Model {0} is disabled.").format(model), title=_("Disabled Model"))
	provider = resolve_provider_credentials(doc.model_id)
	config = {
		"model": doc.model_id,
		"api_key": doc.get_password("api_key", raise_exception=False) or provider.get("api_key"),
		"api_base": doc.base_url or provider.get("base_url"),
	}
	if model_params := doc.model_params():
		config["model_params"] = model_params
	return config


def served_by_flow_server(model_id: str) -> bool:
	"""Whether the flow server's own adapter serves the model, such as a ChatGPT
	subscription's codex/*. litellm does not know these; the server holds their sign-in."""
	import litellm
	from flow_harness.model.catalog import provider_for_model

	spec = provider_for_model(model_id)
	return spec is not None and spec.id not in {p.value for p in litellm.provider_list}


def ping_through_flow_server(model: str) -> None:
	"""Send one message to `model` on a throwaway flow server session, the only place a
	model the server serves itself can be reached. Throws the run's error."""
	from frappe.ai.daemon import lifecycle
	from frappe.ai.lib.session import flow_server

	sid = f"ping-{frappe.generate_hash(length=10)}"
	config = {
		"session_id": sid,
		"title": "Connection test",  # a titled session skips the titling call
		**model_config(model),
		"max_turns": 1,
		"cwd": str(lifecycle.session_root()),
	}
	with flow_server() as client:
		client.create_session(config)
		try:
			client.run(sid, "ping")
			error = run_error(client, sid)
		finally:
			discard_session(client, sid)
	if error:
		frappe.throw(error, title=_("Connection Failed"))


def run_error(client: DaemonClient, sid: str) -> str | None:
	"""Wait up to PING_TIMEOUT for the session's run to end; its error message, if it failed."""
	deadline = time.monotonic() + PING_TIMEOUT
	since = 0
	while time.monotonic() < deadline:
		for entry in client.entries(sid, since=since, path="all")["entries"]:
			since = entry["seq"]
			if entry["type"] == "run_error":
				return entry["message"]
			if entry["type"] == "run_ended":
				return None
		time.sleep(0.5)
	return _("The model did not answer within {0} seconds.").format(PING_TIMEOUT)


def discard_session(client: DaemonClient, sid: str) -> None:
	"""Delete the throwaway session, aborting a run still going first, since the server
	refuses to delete a running session. Its own failures never hide the check's error."""
	with suppress(DaemonError):
		for _attempt in range(20):
			if not client.get_session(sid)["running"]:
				break
			client.abort(sid)
			time.sleep(0.25)
		client.delete_session(sid)


def resolve_provider_credentials(model_id: str) -> dict[str, Any]:
	"""Look up central Flow Provider credentials for a model's provider."""
	provider = model_provider(model_id)
	if not provider or not frappe.db.exists("Flow Provider", provider):
		return {}

	doc = frappe.get_doc("Flow Provider", provider)
	if not doc.enabled:
		return {}

	return {
		"api_key": doc.get_password("api_key", raise_exception=False) or None,
		"base_url": doc.base_url or None,
	}


def model_provider(model_id: str) -> str | None:
	"""The Flow Provider name a model id belongs to, if any."""
	if model_id.partition("/")[0] == CLAUDE_CODE:
		return CLAUDE_CODE
	try:
		import litellm

		return litellm.get_llm_provider(model_id)[1]
	except Exception:
		return None


def ensure_claude_code_model() -> None:
	"""The Claude Code provider and its Opus model, on its CLI login until a token is set.
	The first model a site gets becomes the Assistant's."""
	if not frappe.db.exists("Flow Provider", CLAUDE_CODE):
		frappe.get_doc({"doctype": "Flow Provider", "provider": CLAUDE_CODE}).insert(ignore_permissions=True)
	if not frappe.db.exists("Flow Model", CLAUDE_CODE_MODEL):
		frappe.get_doc(
			{"doctype": "Flow Model", "title": CLAUDE_CODE_MODEL, "provider": CLAUDE_CODE, "model_id": "opus"}
		).insert(ignore_permissions=True)
