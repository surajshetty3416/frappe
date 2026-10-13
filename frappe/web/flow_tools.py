"""Tools that let the AI layer (flow) build the website with Builder. Listed under the
`flow_tools` hook, so every flow agent can attach them."""

from typing import Annotated

import frappe
from frappe import _
from frappe.ai import artifacts, tool
from frappe.ai.lib.tool import ToolContext
from frappe.web.ai.block_codec import BlockCodec
from frappe.web.ai.page_writer import (
	expand_page_yaml,
	load_page_root,
	new_block_id,
	normalize_styles,
	persist_page,
	save_draft_blocks,
)
from frappe.web.page_blocks.chat import ChatBlock
from frappe.web.page_blocks.form import FormBlock

PAGE_YAML_GUIDE = f"""Create a website page with Frappe Builder; its editor opens beside the chat. The page stays a draft until it is published.

page_yaml is one YAML block tree whose root is `el: body`. Block keys: {BlockCodec.fields_doc()}. Every block is a flex or block box styled with CSS-in-JS (camelCase properties, string values with units); text goes in `text` (inline HTML allowed); children go in `c`; links and images use attrs (href, src, alt). Example:

el: body
style: {{display: flex, flexDirection: column, fontFamily: Inter}}
c:
  - el: section
    style: {{padding: 96px 24px, display: flex, flexDirection: column, alignItems: center, gap: 16px}}
    c:
      - el: h1
        text: Fresh bread, every morning
        style: {{fontSize: 56px, fontWeight: '700', margin: '0'}}
      - el: a
        text: See the menu
        attrs: {{href: /menu}}
        style: {{padding: 12px 20px, background: '#111', color: '#fff', borderRadius: 8px}}

Write real, specific copy from the conversation, never placeholder text."""


@tool
def list_web_pages(
	search: Annotated[str, "Words to look for in page titles and routes; empty lists the latest"] = "",
	*,
	ctx: ToolContext,
) -> list[dict]:
	"""List the website's Builder pages, newest first, with the link to edit each one and its live URL if published."""
	or_filters = {"page_title": ["like", f"%{search}%"], "route": ["like", f"%{search}%"]} if search else None
	pages = frappe.get_list(
		"Builder Page",
		fields=["name", "page_title", "route", "published"],
		or_filters=or_filters,
		order_by="modified desc",
		limit=20,
	)
	return [
		{
			**page,
			"editor": artifacts.route("Builder Page", page.name),
			"url": f"/{page.route}" if page.published else None,
		}
		for page in pages
	]


@tool(
	description=PAGE_YAML_GUIDE,
	requires_confirmation=True,
	confirm_prompt=lambda args: _("Create the page {0} at /{1}").format(args.get("title"), args.get("route")),
)
def create_web_page(
	title: Annotated[str, "Page title"],
	route: Annotated[str, "URL path without the leading slash, e.g. about or products/bread"],
	page_yaml: Annotated[str, "The page's block tree in Builder's YAML format"],
	*,
	ctx: ToolContext,
) -> dict:
	if not expand_page_yaml(page_yaml)[0]:
		frappe.throw(_("page_yaml has no blocks Builder can read. The root must be a block with `el: body`."))
	page = frappe.get_doc(
		{"doctype": "Builder Page", "page_title": title, "route": route.strip("/")}
	).insert()
	persist_page(page.name, page_yaml)
	artifact = artifacts.link(ctx.session_id, "Builder Page", page.name)
	return {
		"page": page.name,
		"editor": artifact["route"],
		"preview": f"{artifact['route']}/preview",
		"artifact": artifact,
	}


@tool(
	requires_confirmation=True,
	confirm_prompt=lambda args: _("Publish the page {0}").format(args.get("page")),
)
def publish_web_page(
	page: Annotated[str, "The Builder Page name, e.g. page-1a2b3c4d"], *, ctx: ToolContext
) -> dict:
	"""Publish a Builder page's draft so it is live on the website."""
	doc = frappe.get_doc("Builder Page", page)
	doc.publish()
	artifact = artifacts.link(ctx.session_id, "Builder Page", doc.name)
	return {"url": f"/{doc.route}", "editor": artifact["route"], "artifact": artifact}


BLOCK_STYLE = {"width": "100%", "maxWidth": "640px", "marginLeft": "auto", "marginRight": "auto"}
ROOT_BLOCK_STYLE = {"paddingLeft": "20px", "paddingRight": "20px", "boxSizing": "border-box"}
STYLE_HINT = (
	"CSS-in-JS for the block's box, merged over width 100%, maxWidth 640px, centred. Match the page: "
	"the block inherits its font and text color, and takes these custom properties: --fb-accent and "
	"--fb-accent-ink (button and focus color, and its text), --fb-radius, --fb-border, --fb-field-bg, "
	"--fb-error, --fb-gap"
)


@tool(
	requires_confirmation=True,
	confirm_prompt=lambda args: _("Add a form that inserts {0} to the page {1}").format(
		args.get("doctype"), args.get("page")
	),
)
def add_form_block(
	page: Annotated[str, "The Builder Page name, e.g. page-1a2b3c4d"],
	doctype: Annotated[str, "The DocType a submission inserts"],
	fields: Annotated[list[str], "The fieldnames the visitor fills in, in order"],
	submit_label: Annotated[str, "The button's text, e.g. Register"] = "Submit",
	success_message: Annotated[str, "Shown in place of the form after a submission"] = "",
	success_route: Annotated[
		str, "A path to open after a submission instead of the message, e.g. /thanks"
	] = "",
	allow_guest: Annotated[
		bool,
		"Let visitors submit although Guest has no create permission on the DocType. Prefer giving Guest create permission",
	] = False,
	columns: Annotated[int, "Fields per row on a wide screen; phones always show one"] = 1,
	inside: Annotated[
		str, "The name of the block to add it to, as its last child; empty adds it at the end of the page"
	] = "",
	style: Annotated[dict | None, STYLE_HINT] = None,
	*,
	ctx: ToolContext,
) -> dict:
	"""Add a form to a web page that inserts a document of a DocType when a site visitor submits it. It shows each field's label, a mark on required ones, the options of Select and Link fields, and a message under a field the visitor got wrong. Text fields take a full row. It supports Data, numbers, dates, Select, Link, Check and text fields, not attachments or tables. Visitors are rate-limited and bots meet a honeypot. Publish the page to make the form live."""
	config = FormBlock.clean(
		{
			"doctype": doctype,
			"fields": fields,
			"submit_label": submit_label,
			"success_message": success_message,
			"success_route": success_route,
			"allow_guest": allow_guest,
		}
	)
	block_style = {**BLOCK_STYLE, **normalize_styles(style)}
	if columns > 1:
		block_style["--fb-columns"] = str(columns)
	block = {"element": "div", "blockName": f"{doctype} form", "baseStyles": block_style, "form": config}
	result = add_block(page, block, inside, ctx)
	result["warnings"] = FormBlock(config).warnings()
	return result


@tool(
	requires_confirmation=True,
	confirm_prompt=lambda args: _(
		"Add a chat with {0} to the page {1}. {0} becomes public: site visitors can chat with it, and its tools run as Guest."
	).format(args.get("agent"), args.get("page")),
)
def add_chat_block(
	page: Annotated[str, "The Builder Page name, e.g. page-1a2b3c4d"],
	agent: Annotated[str, "The Flow Agent visitors talk to"],
	title: Annotated[str, "The chat's heading; defaults to the agent's title"] = "",
	greeting: Annotated[str, "The agent's first message, shown before the visitor writes"] = "",
	placeholder: Annotated[str, "The empty composer's hint, e.g. Ask about the schedule"] = "",
	inside: Annotated[
		str, "The name of the block to add it to, as its last child; empty adds it at the end of the page"
	] = "",
	style: Annotated[dict | None, STYLE_HINT + ", --fb-chat-height (default 480px)"] = None,
	*,
	ctx: ToolContext,
) -> dict:
	"""Add a chat to a web page where a site visitor talks to one agent, and make that agent public. Every visitor chats as Guest, so the agent's tools read only DocTypes that give Guest read permission; give Guest read on what it must answer from, and nothing private. A tool call that needs approval is declined, since a visitor cannot approve it. Visitors see the answers only, with no tool calls, and are rate-limited. A public agent cannot have update_memory or execute. Publish the page to make the chat live."""
	agent_doc = frappe.get_doc("Flow Agent", agent)
	if not agent_doc.public:
		agent_doc.public = 1
		agent_doc.save()
	config = ChatBlock.clean(
		{"agent": agent, "title": title, "greeting": greeting, "placeholder": placeholder}
	)
	block = {
		"element": "div",
		"blockName": f"Chat with {agent_doc.title}",
		"baseStyles": {**BLOCK_STYLE, **normalize_styles(style)},
		"chat": config,
	}
	result = add_block(page, block, inside, ctx)
	result["guest_can_read"] = [
		doctype
		for doctype in frappe.get_all(
			"DocType", filters={"istable": 0, "issingle": 0, "custom": 1}, pluck="name"
		)
		if frappe.has_permission(doctype, "read", user="Guest")
	]
	return result


@tool(
	requires_confirmation=True,
	confirm_prompt=lambda args: _("Set the data script of the page {0}").format(args.get("page")),
)
def set_page_data_script(
	page: Annotated[str, "The Builder Page name, e.g. page-1a2b3c4d"],
	script: Annotated[str, "Python that fills the dict `data`, e.g. data.speakers = frappe.get_all(...)"],
	*,
	ctx: ToolContext,
) -> dict:
	"""Set the Python that fills a page's data on every visit, so the page shows live records. It runs in the server script sandbox, as the visitor, and frappe.get_all reads past permissions, so fetch only what the page shows. Read the values in the page's blocks with `repeat: {data: <key>, item: <block>}` and `bind: {text: <field>}` inside the item, or `bind: {text: <key>}` outside one. The script is live at once, on the draft and the published page. Returns a sample of the data it made."""
	doc = frappe.get_doc("Builder Page", page)
	doc.check_permission("write")
	doc.page_data_script = script
	data = doc.get_page_data()
	frappe.db.set_value("Builder Page", page, "page_data_script", script, update_modified=True)
	artifact = artifacts.link(ctx.session_id, "Builder Page", page)
	return {"page": page, "data": data_sample(data), "artifact": artifact}


def add_block(page: str, block: dict, inside: str, ctx: ToolContext) -> dict:
	"""Append `block` to the page's draft, inside the block named `inside` or at the end."""
	frappe.get_doc("Builder Page", page).check_permission("write")
	root = load_page_root(page)
	if not root:
		frappe.throw(_("The page {0} has no blocks yet. Create it with create_web_page first.").format(page))
	parent = find_named_block(root, inside) if inside else root
	if not parent:
		frappe.throw(_("The page has no block named {0}.").format(inside))
	if parent is root:
		# the page body has no side padding, so the block keeps off a phone's edges itself
		block["baseStyles"] = {**ROOT_BLOCK_STYLE, **block["baseStyles"]}
	block["blockId"] = new_block_id()
	parent.setdefault("children", []).append(block)
	save_draft_blocks(page, root)
	artifact = artifacts.link(ctx.session_id, "Builder Page", page)
	return {"page": page, "block": block["blockId"], "editor": artifact["route"], "artifact": artifact}


def find_named_block(block: dict, name: str) -> dict | None:
	if block.get("blockName") == name:
		return block
	for child in block.get("children") or []:
		if isinstance(child, dict) and (found := find_named_block(child, name)):
			return found
	return None


def data_sample(data: dict) -> dict:
	"""Each key's value, with a list cut to its count and first two items."""
	return {
		key: {"count": len(value), "first": value[:2]} if isinstance(value, list) else value
		for key, value in frappe.parse_json(frappe.as_json(data)).items()
	}
