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

	def test_a_record_links_to_its_full_form(self):
		mine = todo(WORKER, "Call the venue")
		self.assertEqual(workspace.get_record("ToDo", mine)["url"], f"/desk/todo/{mine}")


TASKS = {
	"type": "queue",
	"title": "Tasks to settle",
	"doctype": "ToDo",
	"filters": {"allocated_to": "@me", "status": "Open"},
	"fields": ["description"],
	"actions": [
		{"label": "Drop", "kind": "set", "field": "status", "value": "Cancelled", "comment": "required"},
		{"label": "Finish", "kind": "set", "field": "status", "value": "Closed", "fields": ["date"]},
		{"label": "Raise", "kind": "set", "field": "priority", "value": "High"},
	],
}


class TestTaskActions(IntegrationTestCase):
	def setUp(self):
		user(WORKER)
		for name in frappe.get_all("ToDo", filters={"allocated_to": WORKER}, pluck="name"):
			frappe.delete_doc("ToDo", name, force=True, ignore_permissions=True)
		frappe.set_user(WORKER)
		self.queue = workspace.save_workspace([TASKS])[0]["id"]

	def tearDown(self):
		frappe.set_user(WORKER)
		workspace.reset_workspace()
		frappe.set_user("Administrator")

	def comments(self, name: str) -> list[str]:
		return frappe.get_all(
			"Comment",
			filters={"reference_doctype": "ToDo", "reference_name": name, "comment_type": "Comment"},
			pluck="content",
		)

	def test_an_action_that_needs_a_reason_asks_for_it_and_keeps_it(self):
		mine = todo(WORKER, "Call the venue")
		with self.assertRaises(frappe.ValidationError):
			workspace.act(self.queue, 0, mine)
		workspace.act(self.queue, 0, mine, comment="The venue cancelled on us.")
		self.assertEqual(frappe.db.get_value("ToDo", mine, "status"), "Cancelled")
		self.assertEqual(self.comments(mine), ["The venue cancelled on us."])

	def test_an_action_saves_the_fields_it_asks_for(self):
		mine = todo(WORKER, "Call the venue")
		workspace.act(self.queue, 1, mine, values={"date": "2026-10-20", "priority": "High"})
		self.assertEqual(
			frappe.db.get_value("ToDo", mine, ["status", "date", "priority"], as_dict=True),
			{"status": "Closed", "date": frappe.utils.getdate("2026-10-20"), "priority": "Medium"},
		)

	def test_what_an_action_did_today_is_listed_and_can_be_undone(self):
		mine = todo(WORKER, "Call the venue")
		handed_on = frappe.get_doc("ToDo", todo(WORKER, "Book the caterer"))
		handed_on.allocated_to = user(OTHER)
		handed_on.save(ignore_version=False)
		workspace.act(self.queue, 1, mine, values={"date": "2026-10-20"})

		done = workspace.get_widget(self.queue)["done"]
		self.assertEqual([entry["name"] for entry in done], [mine])
		self.assertIn("Closed", done[0]["what"])
		self.assertTrue(done[0]["undo"])

		workspace.undo(self.queue, mine)
		self.assertEqual(frappe.db.get_value("ToDo", mine, "status"), "Open")
		self.assertEqual([row.name for row in workspace.get_widget(self.queue)["rows"]], [mine])

	def test_an_assignment_marked_done_keeps_the_note_and_can_be_reopened(self):
		work = todo(WORKER, "Call the venue")
		assignment = (
			frappe.get_doc(
				{
					"doctype": "ToDo",
					"allocated_to": WORKER,
					"description": "Follow up",
					"reference_type": "ToDo",
					"reference_name": work,
				}
			)
			.insert()
			.name
		)
		workspace.respond("assignment", assignment, comment="Called; they confirmed.")
		self.assertEqual(frappe.db.get_value("ToDo", assignment, "status"), "Closed")
		self.assertEqual(self.comments(work), ["Called; they confirmed."])
		self.assertIn(assignment, [entry["name"] for entry in workspace.get_inbox()["done"]])

		workspace.reopen(assignment)
		self.assertEqual(frappe.db.get_value("ToDo", assignment, "status"), "Open")

	def test_a_task_says_who_it_is_from_and_what_was_said(self):
		mine = todo(WORKER, "Call the venue")
		frappe.get_doc("ToDo", mine).add_comment("Comment", "They open at nine.")
		task = workspace.get_task("ToDo", mine)
		self.assertEqual(task["who"], frappe.utils.get_fullname(WORKER))
		self.assertEqual([entry["text"] for entry in task["timeline"]], ["They open at nine."])

	def test_a_record_still_waiting_says_what_was_done_to_it_today(self):
		mine = todo(WORKER, "Call the venue")
		workspace.act(self.queue, 2, mine)
		(row,) = workspace.get_widget(self.queue)["rows"]
		self.assertEqual(row["_did"]["what"], "Priority → High")

	def test_a_home_has_its_own_inbox_whatever_its_spaces_bring(self):
		from unittest.mock import patch

		slice_ = {"id": "approvals", "type": "inbox", "title": "Approvals", "space": "Finance"}
		with patch("frappe.ai.spaces.home_slices", return_value=[slice_]):
			(inbox, _queue) = workspace.get_workspace()["widgets"]
		self.assertEqual((inbox["id"], inbox.get("space"), inbox["title"]), ("inbox", None, None))
		self.assertIn("items", workspace.get_widget(inbox["id"]))


class TestChartWidgets(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		workbook = frappe.get_doc({"doctype": "Insights Workbook", "title": "Widget Charts"}).insert().name
		source = {"type": "table", "data_source": "Site DB", "table_name": "tabToDo"}
		query = frappe.get_doc(
			{
				"doctype": "Insights Query v3",
				"title": "To Dos",
				"workbook": workbook,
				"is_builder_query": 1,
				"use_live_connection": 1,
				"operations": frappe.as_json([{"type": "source", "table": source}]),
			}
		).insert()
		count = {
			"measure_name": "To Dos",
			"column_name": "count",
			"data_type": "Integer",
			"aggregation": "count",
		}
		self.chart = (
			frappe.get_doc(
				{
					"doctype": "Insights Chart v3",
					"title": "To Dos",
					"workbook": workbook,
					"query": query.name,
					"chart_type": "Number",
					"config": frappe.as_json({"number_columns": [count]}),
					"visibility": "Everyone",
				}
			)
			.insert()
			.name
		)

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_a_chart_says_whether_its_reader_may_edit_it(self):
		widgets = [{"id": "to-dos", "type": "chart", "chart": self.chart}]
		self.assertTrue(workspace.with_charts(widgets)[0]["chart_editable"])
		frappe.set_user(user(WORKER))
		(widget,) = workspace.with_charts(widgets)
		self.assertEqual((widget["chart_title"], widget["chart_editable"]), ("To Dos", False))
