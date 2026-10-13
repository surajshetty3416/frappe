# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# License: MIT. See LICENSE

from typing import ClassVar

import frappe
from frappe import _
from frappe.automation_engine.actions.base import AutomationAction, AutomationParamError, render_context


class RunAgent(AutomationAction):
	action_type = "RunAgent"
	label = "Run Agent"
	description = "Start a Flow Agent run with a prompt rendered from the document."
	requires_document = False
	# The agent acts through the Flow server, which a rollback cannot recall.
	transactional = False
	output_schema: ClassVar[dict] = {"destination_reference": {"doctype": "Flow Run", "cardinality": "one"}}
	params_schema: ClassVar[list] = [
		{"fieldname": "agent", "label": "Agent", "fieldtype": "Link", "options": "Flow Agent", "reqd": 1},
		{"fieldname": "prompt", "label": "Prompt", "fieldtype": "Code", "reqd": 1, "templatable": True},
	]

	def validate(self, params, doctype):
		if not params.get("agent") or not frappe.db.exists("Flow Agent", params["agent"]):
			raise AutomationParamError(_("Choose an existing Flow Agent"), fieldname="agent")
		if not (params.get("prompt") or "").strip():
			raise AutomationParamError(_("Prompt is required"), fieldname="prompt")

	def output_doctype(self, params):
		return "Flow Run"

	def execute(self, doc, params, context):
		# nosemgrep: the prompt is a flow param authored by a System Manager, as in render_value.
		prompt = frappe.render_template(params["prompt"], render_context(doc, context))
		run = frappe.get_doc("Flow Agent", params["agent"]).run(
			prompt,
			source="Trigger",
			reference_doctype=doc.doctype if doc else None,
			reference_name=doc.name if doc else None,
		)
		return {
			"detail": _("Started Flow Run {0}").format(run.name),
			"destination_reference": {"doctype": "Flow Run", "name": run.name},
		}
