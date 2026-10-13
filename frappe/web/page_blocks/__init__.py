"""Blocks a Builder Page renders on the server with behaviour of their own: a form that inserts a
document, and a chat with a public agent. A block carries its config under its kind's key
(`form` or `chat`), and the published page is the only source of that config a visitor's
request trusts."""

import html
import json
import os

import bs4 as bs
import frappe
from frappe import _

ASSETS = os.path.join(os.path.dirname(__file__), "assets")


def esc(value) -> str:
	"""HTML-escape a value for text or an attribute. Braces are escaped too, because the
	page's HTML goes through Jinja after it is built."""
	return html.escape(str(value or ""), quote=True).replace("{", "&#123;").replace("}", "&#125;")


def kinds() -> dict:
	from frappe.web.page_blocks.chat import ChatBlock
	from frappe.web.page_blocks.form import FormBlock

	return {FormBlock.key: FormBlock, ChatBlock.key: ChatBlock}


def block_kind(block: dict):
	return next((kind for key, kind in kinds().items() if isinstance(block.get(key), dict)), None)


def clean_config(node: dict) -> dict:
	"""The `form` or `chat` config of a block the agent wrote, checked; {} when it has none."""
	kind = block_kind(node)
	return {kind.key: kind.clean(node[kind.key])} if kind else {}


def render_block(tag, block: dict, state: dict) -> None:
	"""Fill `tag` with a form or chat block's markup, and add the shared assets once."""
	tag.append(bs.BeautifulSoup(render_markup(block_kind(block), block), "html.parser"))
	if not state.get("page_blocks"):
		state["page_blocks"] = True
		state["style_tag"].append(raw(asset("page_blocks.css")))
		state["global_script_tag"].append(raw(asset("page_blocks.js")))


def render_markup(kind, block: dict) -> str:
	try:
		return kind(block[kind.key]).render(block.get("blockId") or "")
	except frappe.ValidationError as exc:
		return f'<p class="fb-unavailable">{esc(exc)}</p>'


def asset(name: str) -> str:
	with open(os.path.join(ASSETS, name)) as f:
		return f.read()


def raw(text: str) -> str:
	return "{% raw %}" + text + "{% endraw %}"


def published_block(page: str, block_id: str, key: str) -> tuple[dict, dict]:
	"""The published page's (name, modified_by) and the `key` config of its block `block_id`."""
	row = frappe.db.get_value(
		"Builder Page", {"name": page, "published": 1}, ["name", "blocks", "modified_by"], as_dict=True
	)
	block = find_block(json.loads(row.blocks or "[]"), block_id) if row else None
	if not block or not isinstance(block.get(key), dict):
		raise frappe.DoesNotExistError(_("This block is not on a published page."))
	return row, block[key]


def find_block(blocks, block_id: str) -> dict | None:
	stack = list(blocks if isinstance(blocks, list) else [blocks])
	while stack:
		block = stack.pop()
		if not isinstance(block, dict):
			continue
		if block.get("blockId") == block_id:
			return block
		stack.extend(block.get("children") or [])
	return None


@frappe.whitelist()
def preview(block: dict | str) -> dict:
	"""A form or chat block's markup and styles, for the editor's canvas."""
	frappe.has_permission("Builder Page", "write", throw=True)
	block = frappe.parse_json(block)
	kind = block_kind(block)
	if not kind:
		frappe.throw(_("The block is not a form or a chat."))
	return {"html": render_markup(kind, block), "css": asset("page_blocks.css")}
