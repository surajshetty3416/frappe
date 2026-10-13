"""Tools that let the AI layer (flow) build apps in Studio. Listed under the `flow_tools` hook, so
every flow agent can attach them. The Apps skill says how to use them."""

from typing import Annotated, Any

import frappe
from frappe import _
from frappe.ai import artifacts, tool
from frappe.ai.lib.tool import ToolContext
from frappe.ui import page_blocks
from frappe.ui.component_registry import get_catalog

SAVE_PAGE_GUIDE = f"""Create or replace one page of a Studio app from a compact tree, and publish it. The page is found by `page`, else by `title` in the app, else created. Load the Apps skill before the first page.

{page_blocks.__doc__}

resources: {{name: {{resource_type: "Document List" | "Document" | "API Resource", document_type, fields, filters, sort_field, sort_order, limit, document_name, url, params, transform}}}}. Read a list as {{{{ name.data }}}}, a Document as {{{{ name.doc }}}}. variables: {{name: initial value}}; the value's JSON type is the variable's type.

A tree that does not fit the components, resources or DocTypes is not saved; the result lists every fix."""


@tool
def list_studio_apps(*, ctx: ToolContext) -> list[dict]:
	"""List the apps built with Studio, with their pages, the link to open each app in the Studio editor and its live route."""
	apps = frappe.get_list(
		"Studio App", fields=["name", "app_title", "route", "app_home"], order_by="modified desc", limit=50
	)
	for app in apps:
		app.pages = frappe.get_list(
			"Studio Page", filters={"studio_app": app.name}, fields=["name", "page_title", "route", "published"]
		)
		app.editor = artifacts.route("Studio App", app.name)
		app.url = f"/{app.route}"
	return apps


@tool(
	requires_confirmation=True,
	confirm_prompt=lambda args: _("Create the app {0}").format(args.get("title")),
)
def create_studio_app(
	title: Annotated[str, "App title shown to its users"],
	route: Annotated[str, "URL path the app is served at, without slashes, e.g. field-sales"] = "",
	*,
	ctx: ToolContext,
) -> dict:
	"""Create a Studio app (a custom UI over the site's DocTypes), with no pages. Build its pages with
	save_studio_page; the first page saved is the app's home. Its editor opens beside the chat."""
	app = frappe.get_doc({"doctype": "Studio App", "app_title": title, "route": route.strip("/") or None})
	app.insert()
	artifact = artifacts.link(ctx.session_id, "Studio App", app.name)
	return {"app": app.name, "editor": artifact["route"], "url": f"/{app.route}", "artifact": artifact}


@tool
def get_studio_components(
	names: Annotated[list[str], "Components to describe; empty lists every component's name"] = [],  # noqa: B006
	*,
	ctx: ToolContext,
) -> str:
	"""The components Studio app pages can use. With names, each one's props (enum values inline),
	required props and named slots; `(no children)` means it takes no default slot."""
	return get_catalog(names)


@tool
def get_studio_page(
	page: Annotated[str, "The Studio Page name, e.g. page-1a2b3c4d"],
	*,
	ctx: ToolContext,
) -> dict:
	"""Read a Studio app page in the compact form save_studio_page takes, including edits a person
	made in the app editor. Change it and save it back whole."""
	doc = frappe.get_doc("Studio Page", page)
	doc.check_permission("read")
	return {
		"page": doc.name,
		"app": doc.studio_app,
		"title": doc.page_title,
		"route": doc.route,
		**page_blocks.from_page(doc),
	}


@tool(
	description=SAVE_PAGE_GUIDE,
	requires_confirmation=True,
	confirm_prompt=lambda args: _("Save the page {0} at {1} in the app {2}").format(
		args.get("title"), args.get("route"), args.get("app")
	),
)
def save_studio_page(
	app: Annotated[str, "The Studio App name"],
	title: Annotated[str, "Page title; also its route name for router.push({name: title})"],
	route: Annotated[str, "Path inside the app, e.g. /queue or /proposal/:name"],
	blocks: Annotated[list[dict[str, Any]], "The page's top-level blocks"],
	resources: Annotated[dict[str, dict[str, Any]], "Data the page fetches, by name"] = {},  # noqa: B006
	variables: Annotated[dict[str, Any], "Page state, by name, with initial values"] = {},  # noqa: B006
	script: Annotated[str, "Optional page script: top-level JS whose bindings the page can name"] = "",
	page: Annotated[str, "The Studio Page name to replace, when renaming a page"] = "",
	*,
	ctx: ToolContext,
) -> dict:
	frappe.has_permission("Studio App", "read", app, throw=True)
	spec = page_blocks.PageSpec(title, blocks, resources, variables, script)
	doc = find_page(app, title, page)
	titles = set(frappe.get_all("Studio Page", filters={"studio_app": app}, pluck="page_title"))
	if not spec.validate(titles):
		return {"saved": False, "errors": spec.errors[:40], "warnings": spec.warnings[:20]}

	doc.update({"page_title": title, "route": "/" + route.strip("/"), **spec.to_page_fields()})
	doc.published, doc.draft_blocks = 1, None
	doc.save()
	doc.validate_conflicts_with_other_pages()

	artifact = artifacts.link(ctx.session_id, "Studio App", app)
	app_route = frappe.db.get_value("Studio App", app, "route")
	return {
		"saved": True,
		"page": doc.name,
		"url": f"/{app_route}{doc.route}",
		"editor": artifact["route"],
		"warnings": spec.warnings[:20],
		"artifact": artifact,
	}


def find_page(app: str, title: str, page: str):
	name = page or frappe.db.get_value("Studio Page", {"studio_app": app, "page_title": title})
	if name:
		doc = frappe.get_doc("Studio Page", name)
		if doc.studio_app != app:
			frappe.throw(_("Page {0} belongs to another app").format(name))
		return doc
	return frappe.new_doc("Studio Page", studio_app=app)
