"""The components Studio's app renderer can render, read from the renderer's own sources, so the
agent's catalog and page validation follow the front end instead of a copy of it.

Names come from `register(...)` in studio/ui/src/globals.ts, props from the JSON types the editor's
props panel reads, and slots from each component's source, like the editor's slot parser."""

import json
import os
import re
from functools import cache

import frappe

CONTAINER = "container"
STUDIO_UI = ("studio", "ui", "src")
SOURCE_ROOTS = (
	("studio", "node_modules", "frappe-ui", "src", "components"),
	("studio", "node_modules", "frappe-ui", "src", "molecules"),
	("studio", "node_modules", "frappe-ui", "src", "charts"),
	("studio", "node_modules", "frappe-ui", "experimental"),
	("studio", "ui", "src", "components", "AppLayout"),
	("ui", "src", "components"),
)
# the editor resolves these to another component's folder (utils/components.ts)
SOURCE_ALIASES = {"DateTimePicker": "DatePicker", "DateRangePicker": "DatePicker"}


def get_component(name: str) -> dict | None:
	return get_registry().get(name)


def get_catalog(names: list[str] | None = None) -> str:
	"""Without `names`, every component's name. With them, one line per component: its props
	(enums inline), required props and named slots."""
	registry = get_registry()
	if not names:
		return ", ".join(sorted(registry))
	lines = []
	for name in names:
		component = registry.get(name)
		if not component:
			lines.append(f"{name}: not a registered component")
			continue
		lines.append(describe(name, component))
	return "\n".join(lines)


def describe(name: str, component: dict) -> str:
	props = ", ".join(f"{prop}{prop_type(spec)}" for prop, spec in component["props"].items())
	line = f"{name}({props})" if component["props"] else name
	if component["required"]:
		line += f" required: {', '.join(component['required'])}"
	slots = component["slots"]
	if named := [slot for slot in slots or [] if slot != "default"]:
		line += f" slots: {', '.join(named)}"
	if slots is not None and "default" not in slots:
		line += " (no children)"
	return line


def prop_type(spec: dict) -> str:
	if enum := spec.get("enum"):
		return ":" + "|".join(str(value) for value in enum)
	if kind := spec.get("type"):
		return ":" + (kind if isinstance(kind, str) else "|".join(kind))
	return ""


@cache
def get_registry() -> dict[str, dict]:
	root = os.path.dirname(frappe.get_app_path("frappe"))
	types = read_json_types(root)
	sources = index_sources(root)
	registry = {CONTAINER: {"props": {}, "required": [], "slots": ["default"]}}
	for name in registered_names(root):
		schema = types.get(name, {})
		registry[name] = {
			"props": {prop: simplify(spec, schema) for prop, spec in schema.get("properties", {}).items()},
			"required": schema.get("required", []),
			"slots": parse_slots(sources.get(SOURCE_ALIASES.get(name, name), "")),
		}
	return registry


def registered_names(root: str) -> list[str]:
	"""The names globals.ts registers: each by name, and the charts in a loop over FRAPPE_UI_CHARTS."""
	source = read(os.path.join(root, *STUDIO_UI, "globals.ts"))
	constants = read(os.path.join(root, *STUDIO_UI, "utils", "constants.js"))
	charts = re.search(r"FRAPPE_UI_CHARTS = \[([^\]]*)\]", constants).group(1)
	return re.findall(r'register\(\s*"(\w+)"', source) + re.findall(r'"(\w+)"', charts)


def read_json_types(root: str) -> dict[str, dict]:
	"""Each component's props schema, with the definitions its $refs point into."""
	folder = os.path.join(root, *STUDIO_UI, "json_types")
	types = {}
	for library in os.listdir(folder):
		if not os.path.isdir(os.path.join(folder, library)):
			continue
		for file in os.listdir(os.path.join(folder, library)):
			name = file.removesuffix(".json")
			definitions = json.loads(read(os.path.join(folder, library, file))).get("definitions", {})
			schema = definitions.get(f"{name}Props") or definitions.get("*") or {}
			types[name] = {**schema, "definitions": definitions}
	return types


def simplify(spec: dict, schema: dict) -> dict:
	if ref := spec.get("$ref"):
		spec = schema["definitions"].get(ref.split("/")[-1], {})
	if "anyOf" in spec:
		kinds = [option.get("type") for option in spec["anyOf"] if isinstance(option.get("type"), str)]
		return {"type": sorted(set(kinds))}
	return {key: spec[key] for key in ("type", "enum") if key in spec}


def index_sources(root: str) -> dict[str, str]:
	sources = {}
	for parts in SOURCE_ROOTS:
		for folder, _dirs, files in os.walk(os.path.join(root, *parts)):
			if "stories" in folder:
				continue
			for file in files:
				if file.endswith(".vue") and not file.endswith(".story.vue"):
					sources.setdefault(file.removesuffix(".vue"), os.path.join(folder, file))
	return sources


def parse_slots(path: str) -> list[str] | None:
	"""Slot names from the template's <slot> tags, or from defineSlots / SlotsType for a component
	that renders in code. None when that cannot be told: no source, or a render function."""
	source = read(path) if path else ""
	if "<template" not in source and "Slots" not in source:
		return None
	slots = []
	for attributes in re.findall(r"<slot\b([^>]*)>", source):
		if re.search(r":name\s*=", attributes):
			continue
		named = re.search(r"(?:^|\s)name\s*=\s*[\"']([^\"']*)[\"']", attributes)
		slots.append(named.group(1) if named else "default")
	for block in re.findall(r"(?:defineSlots|SlotsType)<\{(.*?)\n\s*\}>", source, re.S):
		keys = re.findall(r"^(\s*)[\"']?([\w-]+)[\"']?\??\s*:", block, re.M)
		# a slot's own scope props sit deeper than the slot names
		depth = min((len(indent) for indent, _key in keys), default=0)
		slots += [key for indent, key in keys if len(indent) == depth]
	return list(dict.fromkeys(slots))


def read(path: str) -> str:
	try:
		with open(path) as file:
			return file.read()
	except OSError:
		return ""
