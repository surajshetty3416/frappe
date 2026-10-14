from frappe.tests import UnitTestCase
from frappe.ui.component_registry import get_registry


class TestComponentRegistry(UnitTestCase):
	def test_the_charts_globals_registers_in_a_loop_are_components(self):
		registry = get_registry()
		for name in ("NumberCard", "BarChart", "LineChart", "DonutChart"):
			self.assertIn(name, registry)
		self.assertIn("Button", registry)
