import os

import frappe
from frappe.model import child_table_fields, display_fieldtypes, no_value_fields, std_fields, table_fields
from frappe.utils import sbool

from frappe.ui.constants import STANDARD_COMPONENT_NAMES
from frappe.ui.utils import get_studio_apps


@frappe.whitelist()
def get_app_boot(app_name: str) -> dict:
	app = frappe.get_doc("Studio App", app_name)
	app.check_permission("read")
	return app.get_boot()


@frappe.whitelist()
def get_doctype_fields(doctype: str, with_standard_fields: bool = False) -> list[dict]:
	frappe.has_permission(doctype, ptype="read", throw=True)
	excluded_fieldtypes = (set(no_value_fields) | set(display_fieldtypes)) - set(table_fields)
	fields = [
		field for field in frappe.get_meta(doctype).fields if field.fieldtype not in excluded_fieldtypes
	]
	standard_fields = [frappe._dict(fieldname="name", fieldtype="Data", label="ID")]
	if sbool(with_standard_fields):
		standard_fields += get_meta_fields(doctype)

	existing_fieldnames = {field.fieldname for field in fields}
	fields += [field for field in standard_fields if field.fieldname not in existing_fieldnames]
	return fields


def get_meta_fields(doctype: str) -> list[frappe._dict]:
	"""Standard columns every document table has, plus parent columns for child tables"""
	fields = [frappe._dict(field) for field in std_fields if field["fieldname"] != "name"]
	if frappe.get_meta(doctype).istable:
		fields += [frappe._dict(fieldname=fieldname, fieldtype="Data") for fieldname in child_table_fields]
	return fields


@frappe.whitelist()
def check_app_permission() -> bool:
	if frappe.session.user == "Administrator":
		return True
	if frappe.has_permission("Studio App", ptype="write") and frappe.has_permission(
		"Studio Page", ptype="write"
	):
		return True
	return False


@frappe.whitelist()
def get_custom_vue_components(frappe_app: str) -> list[dict]:
	"""Discover custom Vue SFC components"""
	components = []
	seen_names = set()

	studio_folder = frappe.get_app_source_path(frappe_app, "studio")

	def has_reserved_name(name: str) -> bool:
		if name in STANDARD_COMPONENT_NAMES:
			frappe.log_error(
				title="Studio: Custom component name conflict",
				message=f"Custom component '{component_name}' in {frappe_app}/{studio_app} "
				f"conflicts with a standard component. Skipping.",
			)
			return True
		return False

	def has_conflicting_name(name: str) -> bool:
		if name in seen_names:
			frappe.log_error(
				title="Studio: Duplicate custom component",
				message=f"Custom component '{component_name}' in {frappe_app}/{studio_app} "
				f"conflicts with another component. Skipping.",
			)
			return True
		return False

	for studio_app in get_studio_apps(frappe_app):
		studio_app_dir = os.path.join(studio_folder, studio_app)
		for dirpath, _dirnames, filenames in os.walk(studio_app_dir):
			for filename in sorted(filenames):
				if not filename.endswith(".vue"):
					continue

				component_name = filename[:-4]  # remove .vue
				if has_reserved_name(component_name) or has_conflicting_name(component_name):
					continue

				seen_names.add(component_name)
				file_path = os.path.join(dirpath, filename)

				components.append(
					{
						"component_name": component_name,
						"studio_app": studio_app,
						"file_path": file_path,
						"studio_file_path": os.path.relpath(file_path, studio_app_dir),
					}
				)

	return components


@frappe.whitelist()
def get_studio_page_scripts(frappe_app: str) -> list[dict]:
	"""Discover exported page scripts (<page>.ts) under <app>/studio/<studio_app>/studio_page/.

	Keyed by the page's docname (`page_name`, read from the sibling JSON) so the runtime can load
	a page's compiled setup() module by its docname.
	"""
	scripts = []

	studio_folder = frappe.get_app_source_path(frappe_app, "studio")
	for studio_app in get_studio_apps(frappe_app):
		page_folder = os.path.join(studio_folder, studio_app, "studio_page")
		if not os.path.isdir(page_folder):
			continue

		# each page is a folder holding <stem>.json + <stem>.ts
		for entry in sorted(os.listdir(page_folder)):
			page_dir = os.path.join(page_folder, entry)
			if not os.path.isdir(page_dir):
				continue

			file_path = os.path.join(page_dir, f"{entry}.ts")
			json_path = os.path.join(page_dir, f"{entry}.json")
			if not (os.path.exists(file_path) and os.path.exists(json_path)):
				continue
			page_name = frappe.parse_json(frappe.read_file(json_path)).get("page_name")
			if page_name:
				scripts.append(
					{
						"page_name": page_name,
						"frappe_app": frappe_app,
						"studio_app": studio_app,
						"file_path": file_path,
					}
				)

	return scripts
