"""A Print Format drawn on the HTML canvas. Each save renders the block tree with Builder's
renderer into the format's `html` (Jinja, rendered against the document by the print view) and
its page size and margins into `css`, which the print view and the PDF generator already read."""

import frappe
from frappe.utils import flt
from frappe.utils.jinja import validate_template

from frappe.web.doctype.builder_page.builder_page import get_block_html, get_google_font_urls
from frappe.web.output import load, prepared

# width and height in mm, portrait
PAGE_SIZES = {"A4": (210, 297), "A5": (148, 210), "A6": (105, 148), "Letter": (215.9, 279.4)}
DEFAULT_MARGIN = 10

# The print view loads its own stylesheet and Studio its own reset, so the page sets what both
# would otherwise decide. `:where` keeps these below a block's own class, and the style sits
# after either sheet, so it wins over their bare element rules.
BASE_CSS = """
.fb-print { font-family: Inter, sans-serif; font-size: 12px; line-height: 1.4; color: #111827; display: flex; flex-direction: column; overflow: hidden; }
.fb-print > * { flex-grow: 1; }
:where(.fb-print) *, :where(.fb-print) *::before, :where(.fb-print) *::after { box-sizing: border-box; }
:where(.fb-print) h1, :where(.fb-print) h2, :where(.fb-print) h3, :where(.fb-print) h4, :where(.fb-print) h5, :where(.fb-print) h6, :where(.fb-print) div, :where(.fb-print) p, :where(.fb-print) span, :where(.fb-print) a { margin: 0; padding: 0; font-size: inherit; font-weight: inherit; line-height: inherit; color: inherit; text-decoration: none; }
:where(.fb-print) img, :where(.fb-print) svg { display: block; max-width: 100%; }
:where(.fb-print) img[alt="QR code"] { width: 100%; height: auto; }
"""


def write(doc, method=None):
	"""before_validate: the framework's fields from the canvas, so the format validates its output."""
	root = load(doc)
	if not root:
		return
	doc.custom_format = 1
	doc.print_format_type = "Jinja"
	doc.raw_printing = 0
	doc.print_format_builder = 0
	doc.print_format_builder_beta = 0
	doc.page_size = doc.page_size if doc.page_size in PAGE_SIZES else "A4"
	for side in ("top", "bottom", "left", "right"):
		if not flt(doc.get(f"margin_{side}")):
			doc.set(f"margin_{side}", DEFAULT_MARGIN)
	doc.html = render(root, doc)
	doc.css = page_css(doc)
	validate_template(doc.html)


def page_box(doc) -> dict:
	"""The page in mm, as the preview draws it."""
	width, height = PAGE_SIZES.get(doc.page_size, PAGE_SIZES["A4"])
	margins = {side: flt(doc.get(f"margin_{side}")) for side in ("top", "right", "bottom", "left")}
	return {"size": doc.page_size or "A4", "width": width, "height": height, "margins": margins}


def render(root: dict, doc) -> str:
	content, style, fonts, _dual = get_block_html([prepared(root)])
	# the renderer's slot for a web page's scripts; a printed page runs none
	content = content.replace("<script></script>", "")
	box = page_box(doc)
	inner = box["height"] - box["margins"]["top"] - box["margins"]["bottom"]
	# a hair under the page, so rounding never spills an empty second page
	sized = f".fb-print {{ height: calc({inner}mm - 2px); }}"
	links = "".join(f'<link rel="stylesheet" href="{url}">' for url in get_google_font_urls(fonts))
	css = style.removeprefix("<style>").removesuffix("</style>")
	return f'{links}<style>{BASE_CSS}{sized}{css}</style><div class="fb-print">{content}</div>'


def page_css(doc) -> str:
	"""The page rule the PDF generator reads for margins, `page-size` on .print-format for its
	paper, and the same page on screen for /printview."""
	box = page_box(doc)
	m = box["margins"]
	margins = f"{m['top']}mm {m['right']}mm {m['bottom']}mm {m['left']}mm"
	return (
		f"@page {{ size: {box['size']} portrait; margin: {margins}; }}\n"
		f".print-format {{ page-size: {box['size']}; }}\n"
		"@media screen {\n"
		f"\t.print-format {{ max-width: {box['width']}mm; min-height: {box['height']}mm; padding: {margins}; }}\n"
		"}\n"
	)


def render_for(doc, doctype: str, record: str) -> str:
	from frappe.www.printview import get_html_and_style

	return get_html_and_style(doctype, record, print_format=doc.name, no_letterhead=1)["html"]


def fit_font_size(text, width_mm: float, max_pt: float = 24, min_pt: float = 8, lines: int = 1) -> str:
	"""A font size that fits `text` in `lines` lines `width_mm` wide, for a name on a badge. Jinja
	runs before layout, so it reckons with an average bold glyph instead of measuring."""
	length = max(len(str(text or "")), 1)
	fitting = width_mm * lines * 72 / 25.4 / (length * 0.62)
	return f"{max(min_pt, min(max_pt, round(fitting, 1)))}pt"
