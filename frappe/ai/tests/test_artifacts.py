# Copyright (c) 2026, Frappe Technologies and contributors
# License: MIT. See LICENSE

import frappe
from frappe.ai import artifacts
from frappe.ai.lib.tool import ToolContext
from frappe.ai.permissions import FLOW_USER_ROLE, ensure_flow_role
from frappe.tests import IntegrationTestCase
from frappe.utils import add_to_date, now_datetime

OWNER = "artifacts-owner@example.com"
OTHER = "artifacts-other@example.com"
STUDIO_USER_ROLE = "Studio User"


def user(email: str, *roles: str) -> str:
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": email.split("@")[0], "send_welcome_email": 0}
		).insert(ignore_permissions=True)
	frappe.get_doc("User", email).add_roles(*roles)
	return email


def agent() -> str:
	if frappe.db.exists("Flow Agent", "Artifacts Agent"):
		return "Artifacts Agent"
	model = frappe.get_doc(
		{"doctype": "Flow Model", "title": "Artifacts Model", "model_id": "openai/gpt-4o-mini", "enabled": 1}
	).insert()
	return (
		frappe.get_doc(
			{"doctype": "Flow Agent", "title": "Artifacts Agent", "model": model.name, "instructions": "x"}
		)
		.insert()
		.name
	)


def chat(owner: str, title: str = "A chat", source: str = "Manual") -> str:
	"""A session owned by `owner`, with no flow server twin: these tests never run it."""
	doc = frappe.get_doc({"doctype": "Flow Session", "agent": agent(), "title": title, "source": source})
	current = frappe.session.user
	frappe.set_user(owner)
	try:
		return doc.insert(ignore_permissions=True).name
	finally:
		frappe.set_user(current)


def studio_app(title: str) -> str:
	return frappe.get_doc({"doctype": "Studio App", "app_title": title}).insert().name


def linked(session: str) -> list[tuple[str, str]]:
	return [
		(a.reference_doctype, a.reference_name) for a in frappe.get_doc("Flow Session", session).artifacts
	]


def age(session: str, minutes: int) -> None:
	modified = add_to_date(now_datetime(), minutes=-minutes)
	frappe.db.set_value("Flow Session", session, "modified", modified, update_modified=False)


class ArtifactsTestCase(IntegrationTestCase):
	def setUp(self):
		ensure_flow_role()
		user(OWNER, FLOW_USER_ROLE, STUDIO_USER_ROLE)
		user(OTHER, FLOW_USER_ROLE)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()


class TestArtifacts(ArtifactsTestCase):
	def test_artifact_types_come_from_the_layers_hooks(self):
		types = artifacts.artifact_types()
		self.assertEqual(
			types["Builder Page"],
			{"label": "Web page", "route": "/studio/web/page/{name}", "title_field": "page_title"},
		)
		self.assertEqual(types["Studio App"]["route"], "/studio/ui/app/{name}")
		self.assertIn("Insights Workbook", types)
		self.assertIn("Insights Dashboard v3", types)

	def test_describe_gives_the_label_title_and_studio_route(self):
		app = studio_app("Field Sales")
		self.assertEqual(
			artifacts.describe("Studio App", app),
			{
				"doctype": "Studio App",
				"name": app,
				"label": "App",
				"title": "Field Sales",
				"route": f"/studio/ui/app/{app}",
			},
		)

	def test_link_lists_an_artifact_once_with_the_newest_last(self):
		session = chat(OWNER)
		first, second = studio_app("First App"), studio_app("Second App")
		age(session, 10)
		frappe.set_user(OWNER)

		for app in (first, second, first):
			described = artifacts.link(session, "Studio App", app)

		self.assertEqual(described, artifacts.describe("Studio App", first))
		self.assertEqual(linked(session), [("Studio App", second), ("Studio App", first)])
		self.assertEqual(frappe.get_doc("Flow Session", session).artifacts[-1].title, "First App")
		self.assertGreater(
			frappe.db.get_value("Flow Session", session, "modified"), add_to_date(now_datetime(), minutes=-1)
		)

	def test_a_sync_from_an_older_copy_cannot_drop_a_link(self):
		session = chat(OWNER)
		stale = frappe.get_doc("Flow Session", session)
		artifacts.link(session, "Studio App", studio_app("Kept App"))

		stale.flags.ignore_validate = True
		with self.assertRaises(frappe.TimestampMismatchError):
			stale.save(ignore_permissions=True)

	def test_link_refuses_another_users_chat(self):
		session = chat(OWNER)
		app = studio_app("Not Yours")
		frappe.set_user(OTHER)
		with self.assertRaises(frappe.PermissionError):
			artifacts.link_artifact(session, "Studio App", app)
		self.assertEqual(linked(session), [])

	def test_link_refuses_an_artifact_the_user_cannot_read(self):
		session = chat(OTHER)
		app = studio_app("Hidden App")
		frappe.set_user(OTHER)
		with self.assertRaises(frappe.PermissionError):
			artifacts.link_artifact(session, "Studio App", app)

	def test_link_refuses_a_doctype_that_is_not_an_artifact(self):
		session = chat(OWNER)
		todo = frappe.get_doc({"doctype": "ToDo", "description": "Not an artifact"}).insert()
		with self.assertRaises(frappe.ValidationError):
			artifacts.link_artifact(session, "ToDo", todo.name)

	def test_an_artifact_can_be_deleted_while_linked(self):
		session = chat(OWNER)
		app = studio_app("Short Lived")
		artifacts.link(session, "Studio App", app)

		frappe.delete_doc("Studio App", app)

		frappe.set_user(OWNER)
		self.assertEqual(artifacts.get_session_artifacts(session), [])


class TestHistory(ArtifactsTestCase):
	def test_history_lists_the_users_own_chats_newest_first_with_their_artifacts(self):
		older, newer = chat(OWNER, "Older"), chat(OWNER, "Newer")
		fired, others = chat(OWNER, "Fired", source="Trigger"), chat(OTHER, "Others")
		app = studio_app("History App")
		artifacts.link(older, "Studio App", app)
		for minutes, session in enumerate((newer, older, fired, others), start=1):
			age(session, minutes)
		frappe.set_user(OWNER)

		history = artifacts.get_history(limit=50)

		names = [entry.name for entry in history]
		self.assertLess(names.index(newer), names.index(older))
		self.assertNotIn(fired, names)
		self.assertNotIn(others, names)
		entry = history[names.index(older)]
		self.assertEqual(entry.title, "Older")
		self.assertIn("modified", entry)
		self.assertEqual(entry.artifacts, [artifacts.describe("Studio App", app)])
		self.assertEqual(history[names.index(newer)].artifacts, [])

	def test_history_honours_the_limit(self):
		for title in ("One", "Two", "Three"):
			chat(OWNER, title)
		frappe.set_user(OWNER)
		self.assertEqual(len(artifacts.get_history(limit=2)), 2)

	def test_history_leaves_out_artifacts_the_user_cannot_open(self):
		session = chat(OTHER)
		app = studio_app("Lost Access")
		artifacts.link(session, "Studio App", app)
		frappe.set_user(OTHER)

		entry = next(e for e in artifacts.get_history() if e.name == session)

		self.assertEqual(entry.artifacts, [])

	def test_the_artifacts_chat_is_the_users_latest_one_on_it(self):
		app, untouched = studio_app("Shared App"), studio_app("Untouched App")
		earlier, later = chat(OWNER, "Earlier"), chat(OWNER, "Later")
		others = chat(OTHER, "Others")
		for session in (earlier, later, others):
			artifacts.link(session, "Studio App", app)
		frappe.set_user(OWNER)

		found = artifacts.get_artifact_session("Studio App", app)

		self.assertEqual((found.name, found.title), (later, "Later"))
		self.assertIsNone(artifacts.get_artifact_session("Studio App", untouched))

	def test_a_chats_artifacts_are_private_to_its_owner(self):
		session = chat(OWNER)
		app = studio_app("Private App")
		artifacts.link(session, "Studio App", app)

		frappe.set_user(OWNER)
		self.assertEqual(artifacts.get_session_artifacts(session), [artifacts.describe("Studio App", app)])
		frappe.set_user(OTHER)
		with self.assertRaises(frappe.PermissionError):
			artifacts.get_session_artifacts(session)


class TestLayerTools(ArtifactsTestCase):
	def setUp(self):
		super().setUp()
		self.session = chat("Administrator")
		self.ctx = ToolContext(session_id=self.session, agent=agent(), user="Administrator")

	def test_create_studio_app_opens_the_app_beside_the_chat(self):
		from frappe.ui.flow_tools import create_studio_app

		result = create_studio_app(title="Tool App", ctx=self.ctx)

		self.assertEqual(result["artifact"], artifacts.describe("Studio App", result["app"]))
		self.assertEqual(result["editor"], f"/studio/ui/app/{result['app']}")
		self.assertEqual(linked(self.session), [("Studio App", result["app"])])

	def test_create_and_publish_web_page_link_the_page(self):
		from frappe.web.flow_tools import create_web_page, publish_web_page

		page_yaml = "el: body\nc:\n  - el: h1\n    text: Fresh bread, every morning\n"
		created = create_web_page(
			title="Bakery", route="artifacts-test-bakery", page_yaml=page_yaml, ctx=self.ctx
		)
		other = studio_app("In Between")
		artifacts.link(self.session, "Studio App", other)
		published = publish_web_page(page=created["page"], ctx=self.ctx)

		described = artifacts.describe("Builder Page", created["page"])
		self.assertEqual(created["artifact"], described)
		self.assertEqual(created["editor"], f"/studio/web/page/{created['page']}")
		self.assertEqual(created["preview"], f"/studio/web/page/{created['page']}/preview")
		self.assertEqual(published["artifact"], described)
		self.assertEqual(published["url"], "/artifacts-test-bakery")
		self.assertEqual(linked(self.session), [("Studio App", other), ("Builder Page", created["page"])])

	def test_create_dashboard_links_the_dashboard_then_its_workbook(self):
		from frappe.analytics.flow_tools import ChartSpec, create_dashboard

		chart = ChartSpec(title="To Dos", doctype="ToDo", chart_type="Number")
		result = create_dashboard(title="Tool Dashboard", charts=[chart], ctx=self.ctx)

		(_, dashboard), (_, workbook) = linked(self.session)
		self.assertEqual(
			linked(self.session), [("Insights Dashboard v3", dashboard), ("Insights Workbook", workbook)]
		)
		self.assertEqual(result["artifact"], artifacts.describe("Insights Workbook", workbook))
		self.assertEqual(result["workbook"], f"/studio/analytics/workbook/{workbook}")
		self.assertEqual(result["dashboard"], f"/studio/analytics/dashboards/{dashboard}")

	def test_a_tool_cannot_link_into_a_chat_its_user_cannot_write(self):
		from frappe.ui.flow_tools import create_studio_app

		ctx = ToolContext(session_id=chat(OTHER), agent=agent(), user=OWNER)
		frappe.set_user(OWNER)
		with self.assertRaises(frappe.PermissionError):
			create_studio_app(title="Wrong Chat", ctx=ctx)
		# the app was made: the refusal is the link's (the callback's savepoint undoes the app)
		self.assertTrue(frappe.db.exists("Studio App", "wrong-chat"))
		self.assertEqual(linked(ctx.session_id), [])
