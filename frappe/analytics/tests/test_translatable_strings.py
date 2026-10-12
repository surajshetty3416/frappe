"""Insights is a layer of frappe, so frappe's message extractor map is the one its
frontend is extracted with. Without rows for `.ts` and `.tsx` there, labels in
those files are never extracted for translation.
"""

import re
from pathlib import Path

import frappe
from babel.messages.extract import extract_from_dir
from frappe.gettext.translate import PYTHON_KEYWORDS, get_method_map

from frappe.insights.tests.base import InsightsIntegrationTestCase

FRONTEND = Path(frappe.get_app_path("frappe")).parent / "frontend" / "insights" / "src2"

# `__('...')` and `__("...")`, escapes included. A call with a non-literal first
# argument has nothing to extract, so the pattern skips it.
LITERAL_CALL = re.compile(r"__\(\s*(['\"])((?:\\.|(?!\1).)*)\1")


class TestTranslatableStrings(InsightsIntegrationTestCase):
    # @feature settings.translations
    def test_a_label_reaches_the_translator_whatever_file_it_lives_in(self):
        method_map = get_method_map("frappe")

        extracted = set()
        for filename, _lineno, message, _comments, _context in extract_from_dir(
            str(FRONTEND), method_map, keywords=PYTHON_KEYWORDS
        ):
            if filename.endswith((".ts", ".tsx")):
                extracted.add(message if isinstance(message, str) else message[0])

        written = set()
        for suffix in ("*.ts", "*.tsx"):
            for path in FRONTEND.rglob(suffix):
                for match in LITERAL_CALL.finditer(path.read_text()):
                    written.add(match.group(2).replace("\\'", "'").replace('\\"', '"'))

        self.assertEqual(written - extracted, set())
