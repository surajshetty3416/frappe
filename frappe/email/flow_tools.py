"""Tools that let the AI layer (flow) send email. Listed under the `flow_tools` hook."""

from typing import Annotated

import frappe
from frappe.ai import tool
from frappe.ai.lib.tool import ToolContext


@tool
def send_email_template(
	template: Annotated[str, "Name of the Email Template"],
	email_group: Annotated[str, "Name of the Email Group whose members receive the email"],
	subject: Annotated[str | None, "Overrides the template's subject; Jinja is allowed"] = None,
	*,
	ctx: ToolContext,
) -> int:
	"""Queue one email per member of an Email Group, rendered from an Email Template with the member's fields (for example {{ email }}) in the Jinja context. Returns how many emails were queued."""
	frappe.has_permission("Email Template", "read", template, throw=True)
	frappe.has_permission("Email Group", "read", email_group, throw=True)

	email_template = frappe.get_doc("Email Template", template)
	members = frappe.get_all(
		"Email Group Member",
		filters={"email_group": email_group, "unsubscribed": 0},
		fields=["*"],
	)
	for member in members:
		context = {**member, "doc": member}
		rendered = email_template.get_formatted_email(context)
		frappe.sendmail(
			recipients=[member.email],
			subject=frappe.render_template(subject, context) if subject else rendered["subject"],
			message=rendered["message"],
		)
	return len(members)
