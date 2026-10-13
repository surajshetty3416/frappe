"""Tools that let the AI layer (flow) start apps in Studio. Listed under the `flow_tools`
hook, so every flow agent can attach them."""

from typing import Annotated

import frappe
from frappe import _
from frappe.ai import artifacts, tool
from frappe.ai.lib.tool import ToolContext


@tool
def list_studio_apps(*, ctx: ToolContext) -> list[dict]:
	"""List the apps built with Studio, with the link to open each one in the Studio editor and its live route."""
	apps = frappe.get_list("Studio App", fields=["name", "app_title", "route"], order_by="modified desc", limit=50)
	return [{**app, "editor": artifacts.route("Studio App", app.name), "url": f"/{app.route}"} for app in apps]


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
	"""Create a Studio app (a custom UI over the site's DocTypes). Its editor, where the user
	designs its pages, opens beside the chat."""
	app = frappe.get_doc({"doctype": "Studio App", "app_title": title, "route": route.strip("/") or None})
	app.insert()
	artifact = artifacts.link(ctx.session_id, "Studio App", app.name)
	return {"app": app.name, "editor": artifact["route"], "url": f"/{app.route}", "artifact": artifact}
