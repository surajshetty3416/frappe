import click
import frappe
from frappe.commands import get_site, pass_context


@click.command("build-studio-app")
@click.argument("app_name")
@click.option("--site", help="site name")
@pass_context
def build_studio_app(context, app_name: str, site: str | None = None):
	"""Build the studio app"""
	from frappe.ui.doctype.studio_app.studio_app import StudioApp

	if not site:
		site = get_site(context)

	frappe.init(site)
	frappe.connect()
	app = frappe.get_doc("Studio App", app_name)
	result = app.generate_app_build()
	if build_error := result.get("build_error"):
		click.secho(
			f"Build failed for '{app_name}' — see the output above (Error Log: {build_error['error_log']})",
			fg="red",
		)
		raise SystemExit(1)
	print(f"Studio App '{app_name}' built successfully.")


@click.command("watch-studio")
@pass_context
def watch_studio(context):
	"""Watch studio folders and sync changed JSON into the DB"""
	from frappe.ui.watch import watch

	site = get_site(context)
	frappe.init(site)
	frappe.connect()
	try:
		watch(site)
	finally:
		frappe.destroy()


@click.command("studio-demo")
@pass_context
def studio_demo(context):
	"""Set the site up for the Frappeverse demo and replay each of its recorded chats once"""
	from frappe.ai.demo import import_recordings, play, project, setup_site, unplayed
	from frappe.ai.demo.personas import demo_artifacts, setup_personas

	site = get_site(context)
	frappe.init(site)
	frappe.connect()
	frappe.set_user("Administrator")
	try:
		setup_site()
		import_recordings()
		demo_project = project()
		for recording in unplayed():
			state = play(recording.name, demo_project)
			click.echo(f"{recording.title}: {state['status']}, {state['step']} of {state['steps']} steps")
			if state["status"] != "Done":
				click.secho(state["error"] or "", fg="red")
				raise SystemExit(1)
		click.echo("\nOpen /home as:")
		for login in setup_personas(demo_artifacts(demo_project)):
			click.echo(f"  {login['user']} / {login['password']}  {login['persona']}")
	finally:
		frappe.destroy()


commands = [
	build_studio_app,
	studio_demo,
	watch_studio,
]
