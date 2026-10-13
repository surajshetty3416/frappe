"""The HTML canvas's outputs beside the web page: a Print Format and an Email Template keep a
Builder block tree in `canvas_blocks`, and each save writes the framework's own fields from it
(`html` and `css` for print, `response_html` for email), so /printview, the PDF and every sender
read the canvas without knowing it exists."""

import copy
import json

import frappe
from frappe import _

from frappe.web.ai.page_writer import expand_page_yaml
from frappe.web.page_blocks import block_kind

OUTPUTS = {"Print Format": "doc_type", "Email Template": "reference_doctype"}


def expand(tree_yaml: str) -> dict:
	"""The root block of a YAML tree, with `{{ ... }}` text kept as Jinja for the document."""
	blocks, _script = expand_page_yaml(tree_yaml, bindings=False)
	if not blocks:
		frappe.throw(_("The tree has no blocks. The root must be a block with `el: body`."))
	return blocks[0]


def load(doc) -> dict | None:
	try:
		data = json.loads(doc.get("canvas_blocks") or "null")
	except (TypeError, ValueError):
		return None
	if isinstance(data, list):
		data = data[0] if data else None
	return data if isinstance(data, dict) else None


def walk(block: dict):
	yield block
	for child in block.get("children") or []:
		if isinstance(child, dict):
			yield from walk(child)


def prepared(root: dict) -> dict:
	"""A copy to render: the root as a plain box, one set of styles, and each element marked
	with its block id so the editor can select it in the rendered output. Breakpoint styles go:
	a page or an email is one width, and a 105mm page would match a phone's media query."""
	root = copy.deepcopy(root)
	root["element"] = "div"
	root.pop("originalElement", None)
	for block in walk(root):
		block.pop("mobileStyles", None)
		block.pop("tabletStyles", None)
		block["customAttributes"] = {**(block.get("customAttributes") or {}), "data-block-id": block["blockId"]}
	return root


def problems(root: dict) -> list[str]:
	"""What neither print nor email can carry."""
	found = []
	for block in walk(root):
		if block_kind(block):
			found.append(_("Block {0} is a form or chat, which only a web page can hold.").format(label(block)))
		if block.get("dynamicValues") or block.get("isRepeaterBlock"):
			found.append(
				_("Block {0} binds page data. Write Jinja in its text instead, e.g. {{{{ doc.full_name }}}}.").format(
					label(block)
				)
			)
	return found


def label(block: dict) -> str:
	return block.get("blockName") or block.get("element") or block.get("blockId")


def target_doctype(doc) -> str | None:
	return doc.get(OUTPUTS[doc.doctype])


@frappe.whitelist()
def records(doctype: str, name: str, search: str = "") -> list[dict]:
	"""Records of the artifact's DocType to preview it against, newest first."""
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("read")
	target = target_doctype(doc)
	if not target:
		return []
	title_field = frappe.get_meta(target).get_title_field()
	fields = ["name", f"`{title_field}` as title"] if title_field != "name" else ["name"]
	filters = {title_field: ["like", f"%{search}%"]} if search else None
	return frappe.get_list(target, fields=fields, filters=filters, order_by="creation desc", limit=50)


@frappe.whitelist()
def code(doctype: str, name: str) -> dict:
	"""The artifact's own HTML and CSS: a print format's template body and styles, an email's
	markup. The print view's wrapper and base styles are left out."""
	from frappe.web.doctype.builder_page.builder_page import get_block_html
	from frappe.web.utils import readable_css, readable_html

	doc = frappe.get_doc(doctype, name)
	doc.check_permission("read")
	if doctype == "Email Template":
		return {"html": readable_html(doc.response_html)}
	root = load(doc)
	if not root:
		return {"html": readable_html(doc.html), "css": readable_css(doc.css)}
	content, style, _fonts, _dual = get_block_html([prepared(root)])
	return {"html": readable_html(content), "css": readable_css(style + (doc.css or ""))}


@frappe.whitelist()
def preview(doctype: str, name: str, record: str | None = None) -> dict:
	"""The artifact's output for one record, through the framework's own render path."""
	from frappe.web.output import email_template, print_format

	doc = frappe.get_doc(doctype, name)
	doc.check_permission("read")
	target = target_doctype(doc)
	if target and not record:
		record = frappe.db.get_value(target, {}, "name", order_by="creation desc")
	result = {"doctype": target, "record": record}
	if doctype == "Print Format":
		result["page"] = print_format.page_box(doc)
	else:
		result["senders"] = email_template.senders().get(name, [])
	if not (target and record):
		return {**result, "html": "", "error": _("There is no {0} to preview against.").format(target or _("record"))}
	try:
		if doctype == "Print Format":
			result["html"] = print_format.render_for(doc, target, record)
		else:
			result.update(email_template.render_for(doc, target, record))
	except Exception as exc:
		frappe.clear_last_message()
		result["html"] = ""
		result["error"] = str(exc) or exc.__class__.__name__
	return result
