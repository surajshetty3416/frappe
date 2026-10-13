# Copyright (c) 2026, Frappe Technologies and contributors
# License: MIT. See LICENSE

import frappe
from frappe import _


@frappe.whitelist(methods=["POST"])
def send_test_email(email_account: str) -> str:
	"""Send a test email through the account to the signed-in user, now, so a failure shows here."""
	frappe.has_permission("Email Account", "write", email_account, throw=True)
	sender = frappe.db.get_value("Email Account", email_account, "email_id")
	recipient = frappe.db.get_value("User", frappe.session.user, "email")
	frappe.sendmail(
		recipients=recipient,
		sender=sender,
		subject=_("Test email from Studio"),
		message=_("Your outgoing email account {0} works.").format(sender),
		now=True,
	)
	return recipient
