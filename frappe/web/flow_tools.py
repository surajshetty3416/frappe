"""Tools that let the AI layer (flow) build the website with Builder. Listed under the
`flow_tools` hook, so every flow agent can attach them."""

import re
from typing import Annotated
from urllib.parse import quote

import frappe
from bs4 import BeautifulSoup
from frappe import _
from frappe.utils import validate_email_address
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
from frappe.web.utils import compact_json

PAGE_YAML_GUIDE = f"""Create a website page with Frappe Builder; its editor opens beside the chat. The page stays a draft until it is published. If a page already exists at the route, this replaces that page's draft blocks, and the page keeps its name and data script.

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
	route = route.strip("/")
	name = frappe.db.get_value("Builder Page", {"route": route}, order_by="published desc, creation asc")
	page = frappe.get_doc("Builder Page", name) if name else frappe.new_doc("Builder Page", route=route)
	page.page_title = title
	page.save()
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
	# an open editor reloads the page's data
	doc.db_set("page_data_script", script, notify=True)
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


# --- print formats and emails: the same block tree, rendered against a document ---

OUTPUT_TREE_GUIDE = """tree_yaml is one YAML block tree whose root is `el: body`, in the web page format: el, name, style (CSS-in-JS, camelCase, string values with units), attrs (href, src, alt), text (inline HTML), c (children). Text and style values take Jinja against the record as `doc`: `text: "{{ doc.full_name }}"`. Quote any value that starts with `{`. Name the blocks a person may ask about (`name: Ribbon`)."""


@tool(
	description=f"""Create or replace a Print Format drawn on the HTML canvas, for printing and PDFs of one DocType's records. Its editor opens beside the chat with the page at its real size, rendered against a record. Load the Print skill first.

{OUTPUT_TREE_GUIDE} `{{{{ qr_code(doc.<field>, <pixels>) }}}}` in a text draws a QR code. The root fills the page inside the margins, one page per record.

Returns the text the format prints for a sample record, so check it reads right, and `fields_used`, the record's fields it prints. Every field the person asked for must be in it; name any you leave out in your reply.""",
	requires_confirmation=True,
	confirm_prompt=lambda args: _("Save the print format {0} for {1}").format(args.get("name"), args.get("doctype")),
)
def save_print_format(
	name: Annotated[str, "The format's name, e.g. Frappeverse Badge"],
	doctype: Annotated[str, "The DocType it prints"],
	tree_yaml: Annotated[str, "The page's block tree"],
	page_size: Annotated[str, "A4, A5, A6 or Letter, portrait"] = "A4",
	margin_mm: Annotated[float, "The margin on every side, in millimetres"] = 10,
	*,
	ctx: ToolContext,
) -> dict:
	from frappe.web.output import print_format

	if page_size not in print_format.PAGE_SIZES:
		frappe.throw(_("page_size must be one of {0}.").format(", ".join(print_format.PAGE_SIZES)))
	root = checked_tree(tree_yaml, doctype)
	doc = output_doc("Print Format", name, doc_type=doctype, module=module_of(doctype))
	doc.update(
		{
			"page_size": page_size,
			"disabled": 0,
			"canvas_blocks": compact_json(root),
			**{f"margin_{side}": margin_mm for side in ("top", "bottom", "left", "right")},
		}
	)
	print_format.write(doc)
	record = sample_record(doctype)
	if record:
		rendered = render_or_fix(doc.html, {"doc": frappe.get_doc(doctype, record)}, record)
	persist(doc)
	artifact = artifacts.link(ctx.session_id, "Print Format", doc.name)
	return {
		"print_format": doc.name,
		"page": f"{page_size}, {margin_mm}mm margins",
		"fields_used": fields_used(root),
		"sample_record": record,
		"sample_text": plain_text(rendered) if record else None,
		"print_view": f"/printview?doctype={quote(doctype)}&name={quote(record or '')}&format={quote(doc.name)}",
		"artifact": artifact,
	}


@tool(
	description=f"""Create or replace an Email Template drawn on the HTML canvas. It is written as email clients need it: a 600px column of tables with inline styles. Its editor opens beside the chat with the subject and the email rendered against a record. Load the Email skill first.

{OUTPUT_TREE_GUIDE} Flex rows become table columns, a link with a background becomes a button, and relative links become absolute. No icons, SVG or QR codes: Gmail blocks them.

Returns the subject and text for a sample record, so check they read right, and `fields_used`, the record's fields it reads. Name any field the person asked for that it leaves out.""",
	requires_confirmation=True,
	confirm_prompt=lambda args: _("Save the email template {0}").format(args.get("name")),
)
def save_email_template(
	name: Annotated[str, "The template's name, e.g. Registration Confirmed"],
	subject: Annotated[str, "The subject line; Jinja against the record, e.g. Your talk is in: {{ doc.title }}"],
	tree_yaml: Annotated[str, "The email's block tree"],
	doctype: Annotated[str, "The DocType whose record it is rendered against, e.g. Attendee"],
	*,
	ctx: ToolContext,
) -> dict:
	from frappe.web.output import email_template

	root = checked_tree(tree_yaml, doctype, subject)
	if found := email_template.problems(root):
		frappe.throw("\n".join(found))
	doc = output_doc("Email Template", name)
	doc.update({"subject": subject, "reference_doctype": doctype, "canvas_blocks": compact_json(root)})
	email_template.write(doc)
	record = sample_record(doctype)
	if record:
		context = frappe.get_doc(doctype, record).as_dict()
		subject_text = render_or_fix(subject, {**context, "doc": context}, record)
		message = render_or_fix(doc.response_html, {**context, "doc": context}, record)
	persist(doc)
	artifact = artifacts.link(ctx.session_id, "Email Template", doc.name)
	return {
		"email_template": doc.name,
		"fields_used": fields_used(root, subject),
		"sample_record": record,
		"sample_subject": subject_text if record else None,
		"sample_text": plain_text(message) if record else None,
		"artifact": artifact,
	}


@tool
def preview_output(
	doctype: Annotated[str, "Print Format or Email Template"],
	name: Annotated[str, "The format's or template's name"],
	record: Annotated[str, "The record to render it against, by name"],
	*,
	ctx: ToolContext,
) -> dict:
	"""Open a print format or email template beside the chat, rendered against one record, and return the text it renders. Use it when the person asks to see one for a particular record."""
	from frappe.web.output import preview

	result = preview(doctype, name, record)
	if result.get("error"):
		frappe.throw(result["error"])
	target = result["doctype"]
	title = frappe.db.get_value(target, record, frappe.get_meta(target).get_title_field()) or record
	artifact = artifacts.link(ctx.session_id, doctype, name)
	artifact = {**artifact, "title": f"{name} · {title}", "route": f"{artifact['route']}/{quote(record)}"}
	return {
		"record": record,
		"subject": result.get("subject"),
		"text": plain_text(result["html"]),
		"artifact": artifact,
	}


@tool(
	requires_confirmation=True,
	confirm_prompt=lambda args: _("Add a member to the email group {0} for each {1}").format(
		args.get("title"), args.get("doctype")
	),
)
def fill_email_group(
	title: Annotated[str, "The Email Group's title, e.g. Frappeverse 2027 Attendees"],
	doctype: Annotated[str, "The DocType whose records join, e.g. Attendee"],
	email_field: Annotated[str, "The field holding the address; empty finds the DocType's Email field"] = "",
	filters: Annotated[dict | None, "Only records matching these, e.g. {\"status\": \"Confirmed\"}"] = None,
	*,
	ctx: ToolContext,
) -> dict:
	"""Make an Email Group if it is missing, and add one member per record of a DocType with an email address. A record already in the group is skipped, so run it again to add newer records. Sends nothing."""
	meta = frappe.get_meta(doctype)
	field = email_field or next(
		(df.fieldname for df in meta.fields if df.options == "Email" or df.fieldname in ("email", "email_id")), None
	)
	if not field or not meta.get_field(field):
		frappe.throw(_("{0} has no email field. Pass email_field.").format(doctype))
	if not frappe.db.exists("Email Group", title):
		frappe.get_doc({"doctype": "Email Group", "title": title}).insert()
	group = frappe.get_doc("Email Group", title)
	group.check_permission("write")
	existing = set(frappe.get_all("Email Group Member", filters={"email_group": title}, pluck="email"))
	added = 0
	for email in frappe.get_list(doctype, filters=filters, pluck=field, limit=0):
		email = validate_email_address(email or "")
		if not email or email in existing:
			continue
		frappe.get_doc({"doctype": "Email Group Member", "email_group": title, "email": email}).insert()
		existing.add(email)
		added += 1
	return {"email_group": title, "added": added, "members": group.update_total_subscribers()}


def checked_tree(tree_yaml: str, doctype: str, *extra: str) -> dict:
	"""The tree expanded, or an error naming each problem and its fix."""
	from frappe.web.output import expand, problems, walk

	if not frappe.db.exists("DocType", doctype):
		frappe.throw(_("There is no DocType {0}.").format(doctype))
	root = expand(tree_yaml)
	found = problems(root)
	fields = {df.fieldname for df in frappe.get_meta(doctype).fields} | set(frappe.model.default_fields) | {"get"}
	unknown = sorted(set(fields_used(root, *extra)) - fields)
	if unknown:
		found.append(
			_("{0} has no field {1}. Its fields: {2}.").format(
				doctype, ", ".join(unknown), ", ".join(sorted(fields - set(frappe.model.default_fields) - {"get"}))
			)
		)
	if found:
		frappe.throw("\n".join(found))
	return root


DOC_FIELD = re.compile(r"\bdoc\.([A-Za-z_][A-Za-z0-9_]*)")


def fields_used(root: dict, *extra: str) -> list[str]:
	"""The record's fields a tree reads, in the order it first reads them."""
	from frappe.web.output import walk

	texts = [*extra]
	for block in walk(root):
		texts.append(block.get("innerHTML") or "")
		texts.extend(str(value) for value in (block.get("baseStyles") or {}).values())
		texts.extend(str(value) for value in (block.get("attributes") or {}).values())
	return list(dict.fromkeys(field for text in texts for field in DOC_FIELD.findall(text) if field != "get"))


def output_doc(doctype: str, name: str, **values):
	if frappe.db.exists(doctype, name):
		doc = frappe.get_doc(doctype, name)
		doc.check_permission("write")
		return doc
	return frappe.get_doc({"doctype": doctype, "name": name, "__newname": name, **values})


def persist(doc) -> None:
	if frappe.db.exists(doc.doctype, doc.name):
		doc.save()
	else:
		doc.insert()


def module_of(doctype: str) -> str:
	return frappe.db.get_value("DocType", doctype, "module") or "Custom"


def sample_record(doctype: str) -> str | None:
	return frappe.db.get_value(doctype, {}, "name", order_by="creation desc")


def render_or_fix(template: str, context: dict, record: str) -> str:
	try:
		return frappe.render_template(template, context)
	except Exception as exc:
		frappe.throw(_("The Jinja fails against {0}: {1}").format(record, exc))


def plain_text(html: str, limit: int = 600) -> str:
	text = re.sub(r"\s+", " ", BeautifulSoup(html or "", "html.parser").get_text(" ")).strip()
	return text[:limit]
