# Copyright (c) 2026, Frappe Technologies and contributors
# License: MIT. See LICENSE

import frappe
from frappe.ai import home
from frappe.desk.like import toggle_like
from frappe.share import add_docshare
from frappe.tests import IntegrationTestCase

READER = "home-reader@example.com"
EDITOR = "home-editor@example.com"


def user(email: str) -> str:
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": email.split("@")[0], "send_welcome_email": 0}
		).insert(ignore_permissions=True)
	return email


def builder_page(title: str, published: int) -> str:
	return (
		frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_title": title,
				"route": frappe.scrub(title),
				"published": published,
			}
		)
		.insert()
		.name
	)


class TestHome(IntegrationTestCase):
	def setUp(self):
		self.published = builder_page("Home Test Published", 1)
		self.draft = builder_page("Home Test Draft", 0)
		for email in (user(READER), user(EDITOR)):
			add_docshare("Builder Page", self.published, email, read=1, write=int(email == EDITOR))
			add_docshare("Builder Page", self.draft, email, read=1)

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_a_published_page_opens_at_its_route(self):
		frappe.set_user(READER)
		view = home.get_view("Builder Page", self.published)
		self.assertEqual(view["view"], "/home_test_published")
		self.assertEqual(view["route"], f"/studio/web/page/{self.published}")

	def test_a_draft_page_has_nothing_to_view(self):
		frappe.set_user(READER)
		self.assertIsNone(home.get_view("Builder Page", self.draft)["view"])

	def test_only_a_writer_may_edit(self):
		frappe.set_user(READER)
		self.assertFalse(home.get_view("Builder Page", self.published)["can_write"])
		frappe.set_user(EDITOR)
		self.assertTrue(home.get_view("Builder Page", self.published)["can_write"])

	def test_a_reader_cannot_build(self):
		frappe.set_user(READER)
		self.assertFalse(home.get_home()["can_build"])

	def test_pins_are_the_users_own(self):
		frappe.set_user(READER)
		toggle_like("Builder Page", self.published, "Yes")
		pinned = [(row["doctype"], row["name"]) for row in home.get_home()["pinned"]]
		self.assertEqual(pinned, [("Builder Page", self.published)])
		self.assertTrue(home.get_view("Builder Page", self.published)["pinned"])
		frappe.set_user(EDITOR)
		self.assertEqual(home.get_home()["pinned"], [])

	def test_an_unshared_page_cannot_be_opened(self):
		frappe.set_user(user("home-stranger@example.com"))
		with self.assertRaises(frappe.PermissionError):
			home.get_view("Builder Page", self.published)

	def test_a_doctype_without_a_view_cannot_be_opened(self):
		with self.assertRaises(frappe.ValidationError):
			home.get_view("Print Format", "Standard")

	def test_a_new_user_gets_the_default_home(self):
		frappe.set_user(READER)
		home.reset_home_layout()
		self.assertEqual(
			[section["type"] for section in home.get_home()["sections"]], ["pinned", "recent", "browse"]
		)

	def test_a_user_arranges_their_own_home(self):
		frappe.set_user(READER)
		home.save_home_layout(
			[{"type": "embed", "doctype": "Builder Page", "name": self.published}, {"type": "recent"}]
		)
		sections = home.get_home()["sections"]
		self.assertEqual([section["type"] for section in sections], ["embed", "recent"])
		self.assertEqual(sections[0]["view"]["view"], "/home_test_published")
		frappe.set_user(EDITOR)
		self.assertEqual(
			[section["type"] for section in home.get_home()["sections"]], ["pinned", "recent", "browse"]
		)
		frappe.set_user(READER)
		home.reset_home_layout()

	def test_an_embedded_view_the_user_cannot_read_shows_nothing(self):
		frappe.set_user(user("home-stranger@example.com"))
		home.save_home_layout([{"type": "embed", "doctype": "Builder Page", "name": self.published}])
		self.assertIsNone(home.get_home()["sections"][0]["view"])
		home.reset_home_layout()

	def test_only_a_system_manager_sets_everyones_home(self):
		frappe.set_user(READER)
		with self.assertRaises(frappe.PermissionError):
			home.save_home_layout([{"type": "recent"}], for_everyone=True)

	def test_a_section_must_be_one_the_home_knows(self):
		frappe.set_user(READER)
		with self.assertRaises(frappe.ValidationError):
			home.save_home_layout([{"type": "weather"}])
		with self.assertRaises(frappe.ValidationError):
			home.save_home_layout([{"type": "list", "doctype": "Print Format"}])
