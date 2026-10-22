# Copyright (c) 2026, Frappe Technologies and contributors
# License: MIT. See LICENSE

import json

import frappe
from frappe.ai import setup_flow, spaces, workspace
from frappe.tests import IntegrationTestCase

MEMBER = "spaces-member@example.com"
OUTSIDER = "spaces-outsider@example.com"
ADMIN = "spaces-admin@example.com"
OPEN = "Spaces Test Open"
CLOSED = "Spaces Test Closed"


def user(email: str, *roles: str) -> str:
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": email.split("@")[0], "send_welcome_email": 0}
		).insert(ignore_permissions=True)
	frappe.get_doc("User", email).add_roles(*roles)
	return email


def a_call(space: str) -> dict:
	return {"provider": "Test", "url": f"/call/{space}"}


def in_the_call(space: str) -> list[dict]:
	return [{"user": MEMBER, "full_name": "Member", "image": None}]


def space(title: str, roles: list[str] | None = None, widgets: list | None = None) -> str:
	if frappe.db.exists("Workspace", title):
		frappe.delete_doc("Workspace", title, force=True)
	return (
		frappe.get_doc(
			{
				"doctype": "Workspace",
				"label": title,
				"title": title,
				"public": 1,
				"module": spaces.space_module(),
				"content": "[]",
				"roles": [{"role": role} for role in roles or []],
				"widgets": json.dumps(widgets) if widgets else None,
				"quick_lists": [
					{
						"document_type": "ToDo",
						"label": "Open tasks",
						"quick_list_filter": '[["ToDo","status","=","Open"]]',
					}
				],
			}
		)
		.insert(ignore_permissions=True)
		.name
	)


class TestSpaces(IntegrationTestCase):
	def setUp(self):
		user(MEMBER, "Desk User")
		user(OUTSIDER, "Desk User")
		user(ADMIN, "System Manager", "Workspace Manager")
		frappe.db.delete("Space Member", {"user": ("in", (MEMBER, OUTSIDER, ADMIN))})
		self.open = space(
			OPEN,
			widgets=[
				{
					"id": "mine",
					"type": "queue",
					"title": "My tasks",
					"doctype": "ToDo",
					"filters": {"allocated_to": "@me"},
					"home": 1,
				},
				{"id": "all", "type": "queue", "title": "All tasks", "doctype": "ToDo"},
			],
		)
		self.closed = space(CLOSED, roles=["System Manager"])

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_a_workspace_is_a_space_as_it_is(self):
		frappe.set_user(MEMBER)
		widgets = spaces.get_space(self.closed if False else self.open)["widgets"]
		self.assertEqual([widget["id"] for widget in widgets], ["mine", "all"])
		frappe.set_user("Administrator")
		derived = spaces.space_widgets(frappe.get_doc("Workspace", self.closed))
		self.assertEqual([(widget["type"], widget["doctype"]) for widget in derived], [("queue", "ToDo")])

	def test_people_join_and_leave_the_spaces_they_can_see(self):
		frappe.set_user(MEMBER)
		spaces.join_space(self.open)
		self.assertIn(self.open, [row.name for row in spaces.get_spaces()["mine"]])
		self.assertTrue(spaces.get_space(self.open)["joined"])
		spaces.leave_space(self.open)
		self.assertNotIn(self.open, [row.name for row in spaces.get_spaces()["mine"]])

	def test_a_space_for_other_roles_stays_out_of_sight(self):
		frappe.set_user(OUTSIDER)
		self.assertNotIn(self.closed, [row.name for row in spaces.get_spaces()["others"]])
		with self.assertRaises(frappe.PermissionError):
			spaces.join_space(self.closed)
		with self.assertRaises(frappe.PermissionError):
			spaces.get_space(self.closed)

	def test_an_app_gives_a_space_its_call_and_who_is_in_it(self):
		frappe.set_user(MEMBER)
		with self.patch_hooks({"space_call": [], "space_call_people": []}):
			self.assertIsNone(spaces.get_space(self.open)["call"])
			self.assertEqual(spaces.get_call_people(self.open), [])
		hooks = {
			"space_call": ["frappe.ai.tests.test_spaces.a_call"],
			"space_call_people": ["frappe.ai.tests.test_spaces.in_the_call"],
		}
		with self.patch_hooks(hooks):
			self.assertEqual(
				spaces.get_space(self.open)["call"], {"provider": "Test", "url": f"/call/{self.open}"}
			)
			self.assertEqual([person["user"] for person in spaces.get_call_people(self.open)], [MEMBER])
			frappe.set_user(OUTSIDER)
			with self.assertRaises(frappe.PermissionError):
				spaces.get_call_people(self.closed)

	def test_only_a_workspace_manager_adds_someone_else(self):
		frappe.set_user(OUTSIDER)
		with self.assertRaises(frappe.PermissionError):
			frappe.get_doc({"doctype": "Space Member", "space": self.open, "user": MEMBER}).insert()
		frappe.set_user(ADMIN)
		frappe.get_doc({"doctype": "Space Member", "space": self.open, "user": MEMBER}).insert()
		self.assertTrue(frappe.db.exists("Space Member", {"space": self.open, "user": MEMBER}))

	def test_a_members_home_holds_the_spaces_slice(self):
		frappe.set_user(MEMBER)
		spaces.join_space(self.open)
		home = workspace.get_workspace()["widgets"]
		self.assertIn(("mine", self.open), [(widget["id"], widget.get("space")) for widget in home])
		self.assertNotIn("all", [widget["id"] for widget in home])
		mine = frappe.get_doc(
			{"doctype": "ToDo", "allocated_to": MEMBER, "description": "Spaces test"}
		).insert()
		rows = workspace.get_widget("mine", space=self.open)["rows"]
		self.assertEqual([row.name for row in rows], [mine.name])

	def test_only_an_editor_changes_a_spaces_widgets(self):
		frappe.set_user(MEMBER)
		with self.assertRaises(frappe.PermissionError):
			spaces.save_space_widgets(self.open, [{"type": "inbox"}])

	def test_an_admin_sets_up_spaces_and_invites_people_into_them(self):
		frappe.set_user(ADMIN)
		# example.com names no organization, so the guess is what the site saved, or nothing
		self.assertEqual(
			setup_flow.get_setup()["organization"]["name"], (workspace.organization() or {}).get("name") or ""
		)
		setup_flow.invite([{"email": "spaces-invited@example.com", "spaces": [self.closed]}])
		self.assertTrue(
			frappe.db.exists("Space Member", {"space": self.closed, "user": "spaces-invited@example.com"})
		)
		self.assertIn("System Manager", frappe.get_roles("spaces-invited@example.com"))
		frappe.set_user(MEMBER)
		with self.assertRaises(frappe.PermissionError):
			setup_flow.invite([{"email": "spaces-sneaky@example.com", "spaces": []}])
