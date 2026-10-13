# Copyright (c) 2026, Frappe Technologies and contributors
# License: MIT. See LICENSE

"""Model credentials for the flow server."""

from __future__ import annotations

from typing import Any

import frappe
from frappe import _

# runs on Claude Code in the daemon, not through litellm
CLAUDE_CODE = "claude-code"
CLAUDE_CODE_MODEL = "Claude Code Opus"


def model_config(model: str, *, check_permission: bool = True) -> dict[str, Any]:
	"""The daemon's model, api_key, api_base and model_params for a Flow Model the user may use."""
	if check_permission:
		frappe.has_permission("Flow Model", "read", model, throw=True)
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
