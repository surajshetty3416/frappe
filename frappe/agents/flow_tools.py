"""Tools that let the AI layer (flow) run automations. Listed under the `flow_tools` hook, so every
flow agent can attach them. The Agents skill says how to use them."""

from typing import Annotated, Any

from frappe import _
from frappe.ai import tool
from frappe.ai.lib.tool import ToolContext
from frappe.ai.tools.builtins import _error_text
from frappe.agents.api import run_now


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
