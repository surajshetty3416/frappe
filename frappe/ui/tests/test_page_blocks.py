import json

from frappe.tests import UnitTestCase
from frappe.ui.page_blocks import PageSpec


class TestPageBlocks(UnitTestCase):
	def test_slots_name_their_component_as_the_editor_does(self):
		rows = {"name": "ListRows", "id": "ListRows-rows", "slots": {"default": [{"name": "ListRow"}]}}
		root = json.loads(PageSpec("Queue", [rows]).to_page_fields()["blocks"])[0]
		slot = root["children"][0]["componentSlots"]["default"]
		self.assertEqual(slot["slotId"], "ListRows-rows:default")
		self.assertEqual(slot["parentBlockId"], "ListRows-rows")
