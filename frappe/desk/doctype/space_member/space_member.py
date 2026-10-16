# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class SpaceMember(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		space: DF.Link
		user: DF.Link
	# end: auto-generated types

	_DOCTYPE_NAME = "Space Member"

	def validate(self):
		if self.user != frappe.session.user and "Workspace Manager" not in frappe.get_roles():
			frappe.throw(_("Only a Workspace Manager adds someone else to a Space."), frappe.PermissionError)
		from frappe.ai.spaces import visible

		if not visible(frappe.get_doc("Workspace", self.space)):
			frappe.throw(_("You cannot see this Space."), frappe.PermissionError)
		if frappe.db.exists(
			"Space Member", {"space": self.space, "user": self.user, "name": ("!=", self.name)}
		):
			frappe.throw(_("{0} is already in this Space.").format(self.user), title=_("Already a Member"))

	def on_trash(self):
		if self.user != frappe.session.user and "Workspace Manager" not in frappe.get_roles():
			frappe.throw(
				_("Only a Workspace Manager removes someone else from a Space."), frappe.PermissionError
			)
