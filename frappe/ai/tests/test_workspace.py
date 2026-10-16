# Copyright (c) 2026, Frappe Technologies and contributors
# License: MIT. See LICENSE

import frappe
from frappe.ai import workspace
from frappe.ai.permissions import ASSISTANT_USER_ROLE
from frappe.tests import IntegrationTestCase

WORKER = "workspace-worker@example.com"
OTHER = "workspace-other@example.com"


def user(email: str) -> str:
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": email.split("@")[0], "send_welcome_email": 0}
		).insert(ignore_permissions=True)
	return email


def todo(owner: str, description: str) -> str:
	"""An open ToDo that `owner` made for themselves."""
	current = frappe.session.user
	frappe.set_user(owner)
	try:
		return (
			frappe.get_doc({"doctype": "ToDo", "allocated_to": owner, "description": description})
			.insert()
			.name
		)
	finally:
		frappe.set_user(current)


QUEUE = {
	"type": "queue",
	"title": "My open tasks",
	"doctype": "ToDo",
	"filters": {"allocated_to": "@me", "status": "Open"},
	"fields": ["description", "priority"],
	"order_by": "description asc",
	"search": True,
	"search_fields": ["description"],
	"actions": [
		{"label": "Done", "kind": "set", "field": "status", "value": "Closed"},
		{
			"label": "Follow up",
			"kind": "create",
			"doctype": "ToDo",
			"values": {"description": "After {description}"},
		},
		{
			"label": "Escalate",
			"kind": "set",
			"field": "priority",
			"value": "High",
			"when": {"priority": "Medium"},
		},
		{"label": "Take it", "kind": "assign"},
	],
}


class TestWorkspace(IntegrationTestCase):
	def setUp(self):
		user(WORKER)
		user(OTHER)
		for name in frappe.get_all("ToDo", filters={"allocated_to": ("in", (WORKER, OTHER))}, pluck="name"):
			frappe.delete_doc("ToDo", name, force=True, ignore_permissions=True)
		frappe.set_user(WORKER)
		self.widgets = workspace.save_workspace([QUEUE, {"type": "inbox"}])
		self.queue = self.widgets[0]["id"]

	def tearDown(self):
		frappe.set_user(WORKER)
		workspace.reset_workspace()
		frappe.defaults.clear_user_default(workspace.SETUP_KEY)
		frappe.set_user("Administrator")

	def test_a_new_user_gets_the_inbox(self):
		workspace.reset_workspace()
		self.assertEqual([widget["type"] for widget in workspace.get_workspace()["widgets"]], ["inbox"])

	def test_a_queue_shows_only_what_waits_on_the_user(self):
		mine = todo(WORKER, "Call the venue")
		todo(OTHER, "Not mine")
		rows = workspace.get_widget(self.queue)["rows"]
		self.assertEqual([row.name for row in rows], [mine])
		self.assertEqual(rows[0]["_actions"], [0, 1, 2, 3])

	def test_a_queue_searches(self):
		todo(WORKER, "Call the venue")
		found = todo(WORKER, "Book the caterer")
		self.assertEqual(
			[row.name for row in workspace.get_widget(self.queue, txt="caterer")["rows"]], [found]
		)

	def test_a_set_action_moves_the_record(self):
		mine = todo(WORKER, "Call the venue")
		workspace.act(self.queue, 0, mine)
		self.assertEqual(frappe.db.get_value("ToDo", mine, "status"), "Closed")
		self.assertEqual(workspace.get_widget(self.queue)["rows"], [])

	def test_an_action_runs_with_the_users_permissions(self):
		theirs = todo(OTHER, "Not mine")
		with self.assertRaises(frappe.PermissionError):
			workspace.act(self.queue, 0, theirs)
		self.assertEqual(frappe.db.get_value("ToDo", theirs, "status"), "Open")

	def test_a_create_action_fills_values_from_the_row(self):
		mine = todo(WORKER, "Call the venue")
		made = workspace.act(self.queue, 1, mine)
		self.assertEqual(frappe.db.get_value("ToDo", made["name"], "description"), "After Call the venue")

	def test_a_conditional_action_shows_only_on_matching_rows(self):
		mine = todo(WORKER, "Call the venue")
		frappe.db.set_value("ToDo", mine, "priority", "High")
		self.assertEqual(workspace.get_widget(self.queue)["rows"][0]["_actions"], [0, 1, 3])

	def test_a_quick_entry_takes_only_its_fields(self):
		entry = workspace.save_workspace(
			[
				{
					"type": "quick_entry",
					"doctype": "ToDo",
					"fields": ["description"],
					"defaults": {"allocated_to": "@me", "priority": "High"},
				}
			]
		)[0]["id"]
		made = workspace.create(entry, {"description": "Print badges", "priority": "Low"})
		self.assertEqual(
			frappe.db.get_value("ToDo", made["name"], ["description", "priority", "allocated_to"]),
			("Print badges", "High", WORKER),
		)

	def test_the_inbox_closes_the_users_assignments(self):
		mine = todo(WORKER, "Call the venue")
		inbox = workspace.get_widget(self.widgets[1]["id"])["items"]
		self.assertEqual([item["name"] for item in inbox], [mine])
		workspace.respond("assignment", mine)
		self.assertEqual(frappe.db.get_value("ToDo", mine, "status"), "Closed")

	def test_the_inbox_closes_no_one_elses_assignment(self):
		theirs = todo(OTHER, "Not mine")
		with self.assertRaises(frappe.PermissionError):
			workspace.respond("assignment", theirs)

	def test_a_widget_must_be_one_the_workspace_knows(self):
		for widget in (
			{"type": "weather"},
			{"type": "queue"},
			{"type": "queue", "doctype": "ToDo", "fields": ["no_such_field"]},
			{
				"type": "queue",
				"doctype": "ToDo",
				"actions": [{"label": "X", "kind": "set", "field": "status", "value": "Lost"}],
			},
			{"type": "chart", "chart": "no-such-chart"},
		):
			with self.assertRaises(frappe.ValidationError):
				workspace.save_workspace([widget])

	def test_only_a_system_manager_sets_everyones_workspace(self):
		with self.assertRaises(frappe.PermissionError):
			workspace.save_workspace([{"type": "inbox"}], for_everyone=True)

	def test_only_an_admin_sets_up_and_everyone_is_welcomed(self):
		setup = workspace.get_workspace()["setup"]
		self.assertFalse(setup["needed"])
		self.assertTrue(setup["welcome"])
		workspace.dismiss_welcome()
		self.assertFalse(workspace.get_workspace()["setup"]["welcome"])
		frappe.defaults.clear_user_default(workspace.WELCOMED_KEY)

	def test_only_a_system_manager_sets_the_site_up(self):
		self.assertFalse(workspace.get_workspace()["setup"]["site"])
		with self.assertRaises(frappe.PermissionError):
			workspace.configure_site.func(
				organization="Example",
				about="x",
				country="India",
				currency="INR",
				time_zone="Asia/Kolkata",
				ctx=None,
			)

	def test_an_invited_person_can_set_up_with_the_assistant(self):
		frappe.set_user("Administrator")
		workspace.invite_people.func(
			people=[
				{
					"email": "workspace-invited@example.com",
					"first_name": "Invited",
					"roles": ["Website Manager"],
				}
			],
			ctx=None,
		)
		self.assertEqual(
			{"Website Manager", ASSISTANT_USER_ROLE} - set(frappe.get_roles("workspace-invited@example.com")),
			set(),
		)

	def test_an_assign_action_gives_the_record_to_the_user(self):
		mine = todo(WORKER, "Call the venue")
		workspace.act(self.queue, 3, mine)
		self.assertIn(WORKER, frappe.parse_json(frappe.db.get_value("ToDo", mine, "_assign") or "[]"))

	def test_me_resolves_inside_a_pattern(self):
		self.assertEqual(
			workspace.resolve({"_assign": ["like", "%@me%"]}), {"_assign": ["like", f"%{WORKER}%"]}
		)
