# Copyright (c) 2026, Frappe Technologies and contributors
# License: MIT. See LICENSE

import frappe
from frappe.model.document import Document

PROJECT_LEAD = "This chat is part of a Studio project. What the person wrote for every chat in it:"


class StudioProject(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.ai.doctype.studio_project_artifact.studio_project_artifact import StudioProjectArtifact
		from frappe.ai.doctype.studio_project_knowledge_base.studio_project_knowledge_base import (
			StudioProjectKnowledgeBase,
		)
		from frappe.ai.doctype.studio_project_skill.studio_project_skill import StudioProjectSkill
		from frappe.types import DF

		artifacts: DF.Table[StudioProjectArtifact]
		context: DF.LongText | None
		description: DF.SmallText | None
		knowledge_bases: DF.TableMultiSelect[StudioProjectKnowledgeBase]
		skills: DF.TableMultiSelect[StudioProjectSkill]
		title: DF.Data
	# end: auto-generated types

	def validate(self):
		self.validate_resource_access()

	def on_trash(self):
		"""The project's chats go with it. What they made stays."""
		for session in frappe.get_all("Flow Session", filters={"project": self.name}, pluck="name"):
			frappe.delete_doc("Flow Session", session)

	def validate_resource_access(self):
		"""The project's chats load its skills and search its knowledge bases, so whoever adds one
		must be able to read it."""
		before = self.get_doc_before_save()
		for field, doctype, link in (
			("skills", "Flow Skill", "skill"),
			("knowledge_bases", "Flow Knowledge Base", "knowledge_base"),
		):
			added = {row.get(link) for row in self.get(field)} - {
				row.get(link) for row in (before.get(field) if before else [])
			}
			for name in added:
				frappe.has_permission(doctype, "read", name, throw=True)

	def context_prompt(self) -> str:
		"""The `<project>` block a new chat's system prompt ends with. It rides in the system prompt,
		so a chat keeps the context it started with."""
		parts = [f"Project: {self.title}", (self.description or "").strip(), (self.context or "").strip()]
		body = "\n\n".join(part for part in parts if part)
		return f"\n\n<project>\n{PROJECT_LEAD}\n\n{body}\n</project>"


def add_artifact(project: str, doctype: str, name: str) -> None:
	"""List an artifact one of the project's chats made or changed, once. The project keeps it
	after the chat is cleared."""
	frappe.db.get_value("Studio Project", project, "name", for_update=True)
	row = {"parenttype": "Studio Project", "parentfield": "artifacts", "parent": project}
	ref = {"reference_doctype": doctype, "reference_name": name}
	if frappe.db.exists("Studio Project Artifact", {**row, **ref}):
		return
	last = frappe.db.get_value("Studio Project Artifact", row, "idx", order_by="idx desc")
	frappe.get_doc({"doctype": "Studio Project Artifact", **row, **ref, "idx": (last or 0) + 1}).db_insert()
	frappe.get_doc("Studio Project", project).update_modified()
