"""Tools that let the AI layer (flow) run automations and try agents. Listed under the `flow_tools` hook, so every
flow agent can attach them. The Agents skill says how to use them."""

import time
from typing import Annotated, Any

import frappe
from frappe import _
from frappe.ai import tool
from frappe.ai.lib.tool import ToolContext
from frappe.ai.tools.builtins import _error_text
from frappe.agents.api import run_now
from frappe.ai.orchestrator import last_reply


@tool(
	requires_confirmation=True,
	confirm_prompt=lambda args: _("Run the automation {0} on {1} record(s)").format(
		args.get("automation"), len(args.get("names") or []) or 1
	),
)
def run_automation(
	automation: Annotated[str, "The Automation Flow's name"],
	names: Annotated[list[str], "Records of its DocType to run it on; empty for an automation without one"] = [],  # noqa: B006
	*,
	ctx: ToolContext,
) -> dict[str, Any]:
	"""Run an automation once on each of the given existing records, as if its trigger fired for them. The runs start in the background and show under the automation's Runs."""
	started: list[dict[str, Any]] = []
	failures: list[dict[str, Any]] = []
	for name in names or [None]:
		try:
			started.append({"name": name, **run_now(automation, name)})
		except Exception as e:
			failures.append({"name": name, "error": _error_text(e)})
	result: dict[str, Any] = {"automation": automation, "started": started}
	if failures:
		result["failures"] = failures
	return result


# The site's callback waits on this call: stop waiting before the flow server stops waiting for us.
CALLBACK_TIMEOUT = 120  # the flow server's default when the site sets no flow_callback_timeout


@tool(replay_from_recording=True)
def ask_agent(
	agent: Annotated[str, "The Flow Agent's name"],
	message: Annotated[str, "The question or task, as a visitor would send it"],
	*,
	ctx: ToolContext,
) -> dict[str, Any]:
	"""Send a message to an agent in a new session of its own and return its reply, to show that it works. It runs as you, with your permissions; a public agent's visitors run as Guest. A reply that takes too long comes back as status Running: read it later from the session."""
	run = frappe.get_doc("Flow Agent", agent).run(message)
	# the agent's tool calls come back to this site as other requests, and need its rows now
	frappe.db.commit()
	deadline = time.monotonic() + (frappe.conf.flow_callback_timeout or CALLBACK_TIMEOUT) - 20
	status = run.status
	while status == "Running" and time.monotonic() < deadline:
		time.sleep(1)
		frappe.db.commit()  # a fresh snapshot, to see the run end
		status = frappe.db.get_value("Flow Run", run.name, "status")
	return {
		"agent": agent,
		"session": run.session,
		"run": run.name,
		"status": status,
		"reply": last_reply(run.name) or frappe.db.get_value("Flow Run", run.name, "error"),
	}
