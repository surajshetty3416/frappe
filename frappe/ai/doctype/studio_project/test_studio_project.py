# Copyright (c) 2026, Frappe Technologies and contributors
# License: MIT. See LICENSE

import frappe
from frappe.ai import artifacts, projects
from frappe.ai.assistant import ASSISTANT_AGENT_TITLE
from frappe.ai.doctype.flow_skill.flow_skill import expand_skill_command
from frappe.ai.lib.session import new_session
from frappe.ai.lib.tool import ToolContext
from frappe.ai.orchestrator import ORCHESTRATOR_AGENT_TITLE
from frappe.ai.permissions import ASSISTANT_USER_ROLE, ensure_assistant_role
from frappe.ai.tests.test_artifacts import APP_MANAGER_ROLE, agent, studio_app, user
from frappe.ai.tools.builtins import bind_load_skill
from frappe.tests import IntegrationTestCase

OWNER = "project-owner@example.com"
OTHER = "project-other@example.com"
CTX = ToolContext(session_id="test", agent="Artifacts Agent", user=OWNER)


def project(owner: str, skills: list[str] | None = None, **values) -> str:
	"""`owner`'s project; a System Manager gives it `skills`, which the owner cannot read."""
	current = frappe.session.user
	frappe.set_user(owner)
	try:
		name = frappe.get_doc({"doctype": "Studio Project", "title": "Conference", **values}).insert().name
	finally:
		frappe.set_user(current)
	if skills:
		doc = frappe.get_doc("Studio Project", name)
		doc.set("skills", [{"skill": skill} for skill in skills])
		doc.save()
	return name


def skill(title: str, instructions: str) -> str:
	return (
		frappe.get_doc(
			{
				"doctype": "Flow Skill",
				"title": title,
				"description": f"{title} for the conference.",
				"instructions": instructions,
				"enabled": 1,
				"user_invocable": 1,
			}
		)
		.insert()
		.name
	)


def chat(owner: str, project: str | None, title: str = "A chat", agent_name: str | None = None) -> str:
	"""A session with no flow server twin: these tests never run it."""
	doc = frappe.get_doc(
		{"doctype": "Flow Session", "agent": agent_name or agent(), "title": title, "project": project}
	)
	current = frappe.session.user
	frappe.set_user(owner)
	try:
		return doc.insert(ignore_permissions=True).name
	finally:
		frappe.set_user(current)


def run(session: str, status: str, routed_by: str | None = None) -> str:
	"""A turn of `session`; `routed_by` makes it a task that orchestrator chat sent."""
	routed = {"reference_doctype": "Flow Session", "reference_name": routed_by} if routed_by else {}
	return (
		frappe.get_doc({"doctype": "Flow Run", "session": session, "status": status, "input": "Go", **routed})
		.insert(ignore_permissions=True)
		.name
	)


class TestStudioProject(IntegrationTestCase):
	def setUp(self):
		ensure_assistant_role()
		user(OWNER, ASSISTANT_USER_ROLE, APP_MANAGER_ROLE)
		user(OTHER, ASSISTANT_USER_ROLE)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def test_a_chat_in_a_project_starts_with_its_context_and_skills(self):
		builder, style = agent(), skill("Conference Style", "Call it Frappeverse.")
		mine = project(OWNER, skills=[style], context="The venue is Nehru Centre.")
		frappe.set_user(OWNER)

		inside = frappe.get_doc(
			{"doctype": "Flow Session", "agent": builder, "project": mine}
		).server_config()
		outside = frappe.get_doc({"doctype": "Flow Session", "agent": builder}).server_config()

		self.assertIn("The venue is Nehru Centre.", inside["system_prompt"])
		self.assertIn("<name>Conference Style</name>", inside["system_prompt"])
		self.assertNotIn("<project>", outside["system_prompt"])
		self.assertNotIn("Conference Style", outside["system_prompt"])

	def test_only_a_projects_chats_can_load_or_start_its_skills(self):
		builder, style = agent(), skill("Conference Style", "Call it Frappeverse.")
		mine = project(OWNER, skills=[style])
		frappe.set_user(OWNER)

		self.assertEqual(bind_load_skill(builder, mine)(name=style, ctx=CTX), "Call it Frappeverse.")
		self.assertIn(
			"Call it Frappeverse.", expand_skill_command(builder, "/skill:conference-style go", mine)
		)
		with self.assertRaises(frappe.ValidationError):
			bind_load_skill(builder)(name=style, ctx=CTX)
		with self.assertRaises(frappe.ValidationError):
			expand_skill_command(builder, "/skill:conference-style go")

	def test_only_a_skill_its_owner_can_read_joins_a_project(self):
		style = skill("Conference Style", "Call it Frappeverse.")
		mine = project(OWNER)
		frappe.set_user(OWNER)
		doc = frappe.get_doc("Studio Project", mine)
		doc.append("skills", {"skill": style})

		with self.assertRaises(frappe.PermissionError):
			doc.save()

	def test_a_chat_cannot_start_in_someone_elses_project(self):
		builder, theirs = agent(), project(OTHER)
		frappe.set_user(OWNER)

		with self.assertRaises(frappe.PermissionError):
			new_session(builder, project=theirs)

	def test_the_project_keeps_what_its_chats_made_after_they_are_gone(self):
		mine = project(OWNER)
		session = chat(OWNER, mine)
		app = studio_app("Badge Desk")
		frappe.set_user(OWNER)

		artifacts.link(session, "Studio App", app)
		frappe.delete_doc("Flow Session", session)

		made = projects.get_project(mine)["artifacts"]
		self.assertEqual(
			[(row["doctype"], row["name"], row["title"]) for row in made], [("Studio App", app, "Badge Desk")]
		)

		frappe.set_user("Administrator")
		frappe.delete_doc("Studio App", app)
		frappe.set_user(OWNER)
		self.assertEqual(projects.get_project(mine)["artifacts"], [])

	def test_deleting_a_project_deletes_its_chats_and_keeps_what_they_made(self):
		mine = project(OWNER)
		session = chat(OWNER, mine)
		app = studio_app("Badge Desk")
		frappe.set_user(OWNER)
		artifacts.link(session, "Studio App", app)

		frappe.delete_doc("Studio Project", mine)

		self.assertFalse(frappe.db.exists("Flow Session", session))
		self.assertTrue(frappe.db.exists("Studio App", app))

	def test_the_lists_name_the_project_that_made_each_artifact_and_filter_by_it(self):
		mine = project(OWNER)
		session = chat(OWNER, mine)
		made, loose = studio_app("Badge Desk"), studio_app("Loose Desk")
		frappe.set_user(OWNER)
		artifacts.link(session, "Studio App", made)

		every = {row["name"]: row["project"] for row in projects.get_artifacts(["Studio App"])}
		only = [row["name"] for row in projects.get_artifacts(["Studio App"], mine)]

		self.assertEqual(every[made], {"name": mine, "title": "Conference"})
		self.assertIsNone(every[loose])
		self.assertEqual(only, [made])

	def test_running_chats_have_an_open_turn_or_routed_tasks_still_open(self):
		mine = project(OWNER)
		busy = chat(OWNER, mine, "Busy", ASSISTANT_AGENT_TITLE)
		idle = chat(OWNER, mine, "Idle", ASSISTANT_AGENT_TITLE)
		router = chat(OWNER, mine, "Router", ORCHESTRATOR_AGENT_TITLE)
		run(idle, "Completed", routed_by=router)
		task = run(busy, "Running", routed_by=router)
		frappe.set_user(OWNER)

		running = {row["name"]: row for row in projects.get_running_chats(mine)}

		self.assertEqual(set(running), {busy, router})
		self.assertEqual(running[router]["tasks"], {"done": 1, "total": 2})
		self.assertIsNone(running[busy]["tasks"])

		frappe.db.set_value("Flow Run", task, "status", "Completed")
		self.assertEqual(projects.get_running_chats(mine), [])
