"""Tools that let the AI layer (flow) build the website with Builder. Listed under the
`flow_tools` hook, so every flow agent can attach them."""

from typing import Annotated

import frappe
from frappe import _
from frappe.builder.ai.block_codec import BlockCodec
from frappe.builder.ai.page_writer import expand_page_yaml, persist_page
from frappe.builder.hooks import builder_path
from frappe.flow import tool
from frappe.flow.lib.tool import ToolContext

PAGE_YAML_GUIDE = f"""Create a website page with Frappe Builder and open it in the editor. The page stays a draft until it is published.

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


def editor_url(page: str) -> str:
	return f"/{builder_path}/page/{page}"


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
		{**page, "editor": editor_url(page.name), "url": f"/{page.route}" if page.published else None}
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
	page = frappe.get_doc({"doctype": "Builder Page", "page_title": title, "route": route.strip("/")}).insert()
	persist_page(page.name, page_yaml)
	return {"page": page.name, "editor": editor_url(page.name), "preview": f"{editor_url(page.name)}/preview"}


@tool(
	requires_confirmation=True,
	confirm_prompt=lambda args: _("Publish the page {0}").format(args.get("page")),
)
def publish_web_page(page: Annotated[str, "The Builder Page name, e.g. page-1a2b3c4d"], *, ctx: ToolContext) -> dict:
	"""Publish a Builder page's draft so it is live on the website."""
	doc = frappe.get_doc("Builder Page", page)
	doc.publish()
	return {"url": f"/{doc.route}", "editor": editor_url(doc.name)}
