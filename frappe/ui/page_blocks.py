"""A Studio Page as a compact tree the agent writes and reads, turned into the page's own fields
(blocks, resources, variables, script) and checked against the component registry and the
DocTypes it reads, so a bad tree comes back as a list of fixes instead of a blank page.

A block: {name, label, props, style, tablet, mobile, children, slots, events, visible, id}.
`name` is a registered component or `container` (a flex column div unless `style` says otherwise).
Props bind data with "{{ expr }}"; {"$var": "x"} binds a prop two-way to variable x.
An event is a script string, or a list of actions compiled into one script:
  {"set": var, "value": v}, {"save": resource, "name": v, "values": {...}}, {"insert": resource,
  "values": {...}}, {"reload": resource}, {"call": method, "args": {...}, "result": var},
  {"route": page title, "params": {...}}, {"toast": text}, {"script": js}.
Action values are JSON, or "{{ expr }}" read like a prop binding."""

import difflib
import json
import random
import re
import string

import frappe
from frappe.model import default_fields

from frappe.ui.component_registry import CONTAINER, get_component, get_registry

ROOT_STYLE = {
	"display": "flex",
	"flexDirection": "column",
	"flexShrink": 0,
	"width": "inherit",
	"height": "100%",
	"overflowX": "hidden",
	"overflowY": "auto",
	"backgroundColor": "var(--surface-white)",
}
BLOCK_KEYS = {"name", "label", "props", "style", "tablet", "mobile", "children", "slots", "events", "visible", "id"}
RESOURCE_TYPES = ("Document List", "Document", "API Resource")
RESOURCE_KEYS = {
	"resource_type", "document_type", "document_name", "fields", "filters", "limit", "sort_field",
	"sort_order", "url", "method", "params", "transform", "on_success", "on_error", "auto",
	"whitelisted_methods",
}  # fmt: skip
ACTIONS = ("set", "save", "insert", "reload", "call", "route", "toast", "script")
FILTER_OPERATORS = {
	"=", "!=", "<", ">", "<=", ">=", "like", "not like", "in", "not in", "is", "between",
	"timespan", "descendants of", "not descendants of", "ancestors of", "not ancestors of",
}  # fmt: skip
PAGE_NAMES = {"route", "router", "call", "toast", "socket"}
SLOT_SCOPES = {
	"ListRows": {"item", "index", "value", "selected", "active"},
	"Repeater": {"dataItem", "dataIndex", "dataKey"},
}
JS_NAMES = set(
	"true false null undefined NaN Infinity this new typeof instanceof in of void delete await async "
	"function return if else const let var Math Date JSON String Number Boolean Object Array Promise "
	"Intl RegExp parseInt parseFloat isNaN encodeURIComponent decodeURIComponent window document "
	"console navigator location setTimeout clearTimeout event eventArgs".split()
)
IDENTIFIER = re.compile(r"(?<![\w$.])([A-Za-z_$][\w$]*)")
STRING_LITERAL = re.compile(r"'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\"|`(?:\\.|[^`\\])*`")
BINDING = re.compile(r"\{\{(.*?)\}\}", re.S)


class PageSpec:
	"""One page in compact form."""

	def __init__(self, title: str, blocks, resources=None, variables=None, script: str = ""):
		self.title = title
		self.blocks = blocks if isinstance(blocks, list) else [blocks]
		self.resources = resources or {}
		self.variables = variables or {}
		self.script = script or ""
		self.errors: list[str] = []
		self.warnings: list[str] = []

	# page fields

	def to_page_fields(self) -> dict:
		return {
			"blocks": json.dumps([self.root_block()], separators=(",", ":")),
			"resources": [self.resource_row(name, spec) for name, spec in self.resources.items()],
			"variables": [variable_row(name, value) for name, value in self.variables.items()],
			"script": self.script,
		}

	def root_block(self) -> dict:
		return {
			**empty_block("root", "div"),
			"blockName": "body",
			"originalElement": "body",
			"baseStyles": dict(ROOT_STYLE),
			"children": [self.block(node) for node in self.blocks],
		}

	def block(self, node: dict) -> dict:
		name = node["name"]
		block = empty_block(node.get("id") or new_id(name), name)
		if name == CONTAINER:
			block["originalElement"] = "div"
			block["baseStyles"] = {"display": "flex", "flexDirection": "column"}
		block["baseStyles"].update(node.get("style") or {})
		block["tabletStyles"] = node.get("tablet") or {}
		block["mobileStyles"] = node.get("mobile") or {}
		block["componentProps"] = {key: to_prop(value) for key, value in (node.get("props") or {}).items()}
		block["children"] = [self.block(child) for child in node.get("children") or []]
		block["componentSlots"] = {
			slot: self.slot(block["componentId"], slot, content)
			for slot, content in (node.get("slots") or {}).items()
		}
		block["componentEvents"] = {
			event: self.event(event, handler) for event, handler in (node.get("events") or {}).items()
		}
		if label := node.get("label"):
			block["blockName"] = label
		if visible := node.get("visible"):
			block["visibilityCondition"] = visible
		return block

	def slot(self, component_id: str, name: str, content: list) -> dict:
		# the ids the editor gives a slot when it loads the page; without them its first load saves a draft
		return {
			"slotName": name,
			"slotId": f"{component_id}:{name}",
			"parentBlockId": component_id,
			"slotContent": [self.block(child) for child in content],
		}

	def event(self, event: str, handler) -> dict:
		if isinstance(handler, str):
			return {"event": event, "action": "Run Script", "script": handler}
		return {"event": event, "action": "Run Script", "script": self.compile(handler), "actions": handler}

	def compile(self, actions: list) -> str:
		lines = [f"\t{self.statement(action)}" for action in actions]
		return "\n".join(
			[
				"(async () => {",
				*lines,
				"})().catch((error) => toast.error(error?.messages?.[0] || error?.message || String(error)))",
			]
		)

	def statement(self, action: dict) -> str:
		js = self.js
		if "set" in action:
			return f"{action['set']}.value = {js(action.get('value'))}"
		if "save" in action:
			values = dict(action.get("values") or {})
			if "name" in action:
				values = {"name": action["name"], **values}
			return f"await {action['save']}.setValue.submit({js(values)})"
		if "insert" in action:
			return f"await {action['insert']}.insert.submit({js(action.get('values') or {})})"
		if "reload" in action:
			return f"await {action['reload']}.reload()"
		if "call" in action:
			call = f"await call({json.dumps(action['call'])}, {js(action.get('args') or {})})"
			return f"{action['result']}.value = {call}" if action.get("result") else call
		if "route" in action:
			return f"router.push({js({'name': action['route'], 'params': action.get('params') or {}})})"
		if "toast" in action:
			return f"toast.success({js(action['toast'])})"
		return action.get("script", "")

	def js(self, value) -> str:
		"""A JSON value as JS. "{{ expr }}" is the expression, with variables read through .value,
		since a script sees them as refs where a binding sees their values."""
		if isinstance(value, dict):
			return "{" + ", ".join(f"{json.dumps(key)}: {self.js(item)}" for key, item in value.items()) + "}"
		if isinstance(value, list):
			return "[" + ", ".join(self.js(item) for item in value) + "]"
		if not isinstance(value, str) or "{{" not in value:
			return json.dumps(value)
		whole = re.fullmatch(r"\s*\{\{(.*?)\}\}\s*", value, re.S)
		if whole:
			return f"({self.unref(whole.group(1).strip())})"
		parts = []
		for index, piece in enumerate(BINDING.split(value)):
			if index % 2:
				parts.append("${" + self.unref(piece.strip()) + "}")
			else:
				parts.append(piece.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${"))
		return "`" + "".join(parts) + "`"

	def unref(self, expression: str) -> str:
		names = set(self.variables)
		return map_code(
			expression,
			lambda code: IDENTIFIER.sub(
				lambda match: f"{match.group(1)}.value"
				if match.group(1) in names and not is_object_key(code, match.end())
				else match.group(1),
				code,
			),
		)

	def resource_row(self, name: str, spec: dict) -> dict:
		row = {"resource_name": name, **{key: spec[key] for key in RESOURCE_KEYS if key in spec}}
		for key in ("fields", "filters", "params", "whitelisted_methods"):
			if key in row and not isinstance(row[key], str):
				row[key] = json.dumps(row[key])
		if row.get("resource_type") == "Document":
			row["fetch_document_using_filters"] = 0 if spec.get("document_name") else 1
		if row.get("resource_type") == "API Resource":
			# a GET flattens object params, such as filters, to "[object Object]"
			row.setdefault("method", "POST")
		if "sort_order" in row:
			row["sort_order"] = str(row["sort_order"]).upper()
		return row

	# validation

	def validate(self, page_titles: set[str]) -> bool:
		self.page_titles = page_titles | {self.title}
		self.script_names = set(
			re.findall(r"^\s*(?:const|let|var|(?:async\s+)?function)\s+([A-Za-z_$][\w$]*)", self.script, re.M)
		)
		for name, value in self.variables.items():
			if not re.fullmatch(r"[A-Za-z_$][\w$]*", name):
				self.errors.append(f"variables.{name}: a variable name must be a JS identifier")
		for name, spec in self.resources.items():
			self.check_resource(name, spec)
		for index, node in enumerate(self.blocks):
			self.check_block(node, f"blocks[{index}]", set())
		return not self.errors

	@property
	def page_names(self) -> set[str]:
		return set(self.resources) | set(self.variables) | self.script_names | PAGE_NAMES

	def check_resource(self, name: str, spec: dict):
		path = f"resources.{name}"
		if not re.fullmatch(r"[A-Za-z_$][\w$]*", name):
			self.errors.append(f"{path}: a resource name must be a JS identifier")
		if not isinstance(spec, dict):
			return self.errors.append(f"{path}: must be an object")
		if unknown := set(spec) - RESOURCE_KEYS:
			self.errors.append(f"{path}: unknown keys {sorted(unknown)}; allowed {sorted(RESOURCE_KEYS)}")
		kind = spec.get("resource_type")
		if kind not in RESOURCE_TYPES:
			return self.errors.append(f"{path}.resource_type: must be one of {list(RESOURCE_TYPES)}")
		if kind == "API Resource":
			if not spec.get("url"):
				self.errors.append(f"{path}.url: an API Resource needs the whitelisted method path")
			return
		doctype = spec.get("document_type")
		if not doctype or not frappe.db.exists("DocType", doctype):
			return self.errors.append(f"{path}.document_type: no DocType named {doctype!r}")
		known = doctype_fields(doctype)
		if kind == "Document List":
			if not spec.get("fields"):
				self.errors.append(f"{path}.fields: list the fieldnames to fetch")
			for field in spec.get("fields") or []:
				if isinstance(field, str) and "." not in field and " " not in field and field not in known:
					self.errors.append(f"{path}.fields: {doctype} has no field {field!r}{suggest(field, known)}")
			if spec.get("sort_field") and spec["sort_field"] not in known:
				self.errors.append(f"{path}.sort_field: {doctype} has no field {spec['sort_field']!r}")
		elif not spec.get("document_name") and not spec.get("filters"):
			self.errors.append(f"{path}: a Document needs document_name, or filters such as {{\"name\": \"{{{{ route.params.name }}}}\"}}")
		self.check_filters(path, doctype, known, spec.get("filters") or {})

	def check_filters(self, path: str, doctype: str, known: set[str], filters):
		if not isinstance(filters, dict):
			return self.errors.append(f"{path}.filters: must be an object of fieldname: value")
		for field, value in filters.items():
			if field not in known:
				self.errors.append(f"{path}.filters: {doctype} has no field {field!r}{suggest(field, known)}")
			if isinstance(value, list) and (not value or str(value[0]).lower() not in FILTER_OPERATORS):
				self.errors.append(f'{path}.filters.{field}: a list is [operator, value], e.g. ["in", ["A", "B"]]')
			elif isinstance(value, list) and len(value) != 2:
				self.errors.append(f"{path}.filters.{field}: a list filter is exactly [operator, value]")
			for expression in bindings(value):
				self.check_names(f"{path}.filters.{field}", expression, set())
				if expression.strip() in self.variables:
					self.warnings.append(
						f"{path}.filters.{field}: while {expression.strip()} is empty this filters on an empty value; "
						f"write {{{{ {expression.strip()} || null }}}} to drop the filter instead"
					)

	def check_block(self, node, path: str, scope: set[str], item_fields: dict | None = None):
		item_fields = item_fields or {}
		if not isinstance(node, dict) or not isinstance(node.get("name"), str):
			return self.errors.append(f"{path}: a block is an object with a component `name`")
		name = node["name"]
		path = f"{path}({name})"
		if unknown := set(node) - BLOCK_KEYS:
			self.errors.append(f"{path}: unknown keys {sorted(unknown)}; allowed {sorted(BLOCK_KEYS)}")
		component = get_component(name)
		if not component:
			return self.errors.append(f"{path}: not a registered component{suggest(name, set(get_registry()))}")
		self.check_props(path, component, node.get("props") or {}, scope, item_fields)
		self.check_styles(path, node)
		if visible := node.get("visible"):
			for expression in bindings(visible) or [visible]:
				self.check_names(f"{path}.visible", expression, scope, item_fields)
		for event, handler in (node.get("events") or {}).items():
			self.check_event(f"{path}.events.{event}", handler, scope, item_fields)

		slots = component["slots"]
		child_scope, child_fields = self.scope_for(name, node, scope, item_fields)
		if node.get("children") and slots is not None and "default" not in slots:
			self.errors.append(f"{path}.children: {name} has no default slot; use props or slots {slots}")
		if node.get("children") and name == "ListRows":
			self.errors.append(f"{path}.children: put the one row template in slots.default, which gets `item`")
		for index, child in enumerate(node.get("children") or []):
			self.check_block(child, f"{path}.children[{index}]", child_scope, child_fields)
		for slot, content in (node.get("slots") or {}).items():
			if slots is not None and slot not in slots:
				self.errors.append(f"{path}.slots.{slot}: {name} has no slot {slot!r}; its slots are {slots}")
			for index, child in enumerate(content if isinstance(content, list) else []):
				self.check_block(child, f"{path}.slots.{slot}[{index}]", child_scope, child_fields)

	def scope_for(self, name: str, node: dict, scope: set[str], item_fields: dict):
		"""What a component's slot content may name: ListRows' row and Repeater's dataItem, with the
		fields its resource fetches."""
		if name not in SLOT_SCOPES:
			return scope, item_fields
		row = "item" if name == "ListRows" else "dataItem"
		source = (node.get("props") or {}).get("items" if name == "ListRows" else "data")
		fields = None
		match = re.fullmatch(r"\s*\{\{\s*(\w+)\.data\s*\}\}\s*", source) if isinstance(source, str) else None
		if match and (spec := self.resources.get(match.group(1))) and spec.get("resource_type") == "Document List":
			fields = {field for field in spec.get("fields") or [] if isinstance(field, str)} | {"name"}
			if spec.get("transform"):
				fields = None
		return scope | SLOT_SCOPES[name], {**item_fields, row: fields}

	def check_props(self, path: str, component: dict, props: dict, scope: set[str], item_fields: dict):
		known = component["props"]
		for prop in component["required"]:
			if prop not in props:
				self.errors.append(f"{path}.props.{prop}: required")
		for prop, value in props.items():
			spec = known.get(prop)
			if known and spec is None and not prop.startswith("on"):
				self.warnings.append(f"{path}.props.{prop}: not a declared prop; it falls through as an attribute")
			if isinstance(value, dict) and "$var" in value:
				if value["$var"] not in set(self.variables) | self.script_names:
					self.errors.append(f"{path}.props.{prop}: no variable {value['$var']!r}")
				if "debounce" in props:
					self.warnings.append(f"{path}.props.debounce: the input keeps its typed text, so an action that sets {value['$var']} will not clear it")
				continue
			if spec and spec.get("enum") and isinstance(value, str) and "{{" not in value:
				if value not in spec["enum"]:
					self.errors.append(f"{path}.props.{prop}: {value!r} is not one of {spec['enum']}")
			if isinstance(value, str) and len(bindings(value)) > 1 and re.fullmatch(r"\s*\{\{.*\}\}\s*", value, re.S):
				self.errors.append(
					f"{path}.props.{prop}: a value that starts and ends with a binding renders only its first "
					"one; join them in one expression, e.g. {{ a + ' · ' + b }}"
				)
			for expression in bindings(value):
				self.check_names(f"{path}.props.{prop}", expression, scope, item_fields)

	def check_styles(self, path: str, node: dict):
		for key in ("style", "tablet", "mobile"):
			for prop in node.get(key) or {}:
				if not re.fullmatch(r"[a-z][a-zA-Z]*|--[\w-]+", prop):
					self.errors.append(f"{path}.{key}.{prop}: write CSS properties in camelCase")

	def check_event(self, path: str, handler, scope: set[str], item_fields: dict):
		if isinstance(handler, str):
			return
		if not isinstance(handler, list):
			return self.errors.append(f"{path}: an event is a script string or a list of actions")
		for index, action in enumerate(handler):
			self.check_action(f"{path}[{index}]", action, scope, item_fields)

	def check_action(self, path: str, action, scope: set[str], item_fields: dict):
		kind = next((key for key in ACTIONS if isinstance(action, dict) and key in action), None)
		if not kind:
			return self.errors.append(f"{path}: an action has one of {list(ACTIONS)}")
		target = action[kind]
		variables = set(self.variables) | self.script_names
		if kind in ("set",) and target not in variables:
			self.errors.append(f"{path}.set: no variable {target!r}")
		if kind == "call" and action.get("result") and action["result"] not in variables:
			self.errors.append(f"{path}.result: no variable {action['result']!r}")
		if kind in ("save", "insert", "reload"):
			spec = self.resources.get(target)
			if not spec:
				self.errors.append(f"{path}.{kind}: no resource {target!r}")
			elif kind == "save" and spec.get("resource_type") == "Document List" and "name" not in action:
				self.errors.append(f"{path}: saving through a Document List needs the record's `name`")
			elif kind == "insert" and spec.get("resource_type") != "Document List":
				self.errors.append(f"{path}: insert goes through a Document List resource")
			known = spec and spec.get("document_type") and doctype_fields(spec["document_type"])
			if kind in ("save", "insert") and known:
				for field in action.get("values") or {}:
					if field not in known:
						self.errors.append(f"{path}.values: {spec['document_type']} has no field {field!r}{suggest(field, known)}")
		if kind == "route" and target not in self.page_titles:
			self.warnings.append(f"{path}.route: no page titled {target!r} in this app yet")
		for value in [action.get(key) for key in ("value", "name", "values", "args", "params", "toast")]:
			for expression in bindings(value):
				self.check_names(path, expression, scope, item_fields)

	def check_names(self, path: str, expression: str, scope: set[str], item_fields: dict | None = None):
		code = STRING_LITERAL.sub("''", expression)
		if code.count("{") != code.count("}"):
			self.errors.append(
				f"{path}: {{{{ {expression.strip()} }}}} ends at the first '}}}}'; "
				"put spaces between closing braces, e.g. {{ { a: { b: 1 } } }}"
			)
		allowed = self.page_names | scope | JS_NAMES | local_names(expression)
		for name in free_names(expression) - allowed:
			self.errors.append(
				f"{path}: unknown name {name!r} in {{{{ {expression.strip()} }}}}; "
				f"known: {sorted((self.page_names | scope) - PAGE_NAMES)}"
			)
		for row, fields in (item_fields or {}).items():
			for field in re.findall(rf"(?<![\w$.]){row}\.(\w+)", expression):
				if fields is not None and field not in fields:
					self.errors.append(f"{path}: {row}.{field} is not fetched; add {field!r} to the resource's fields")
		for resource, attribute, field in re.findall(r"(?<![\w$.])(\w+)\.(doc|data)\b(?:\.(\w+))?", expression):
			spec = self.resources.get(resource)
			if not spec or spec.get("resource_type") == "API Resource":
				continue
			if attribute == "data" and spec.get("resource_type") == "Document":
				self.errors.append(f"{path}: {resource} is a Document; read it as {resource}.doc")
			elif attribute == "doc" and spec.get("resource_type") == "Document List":
				self.errors.append(f"{path}: {resource} is a Document List; read it as {resource}.data")
			elif attribute == "doc" and field and field not in (doctype_fields(spec["document_type"]) or {field}):
				self.errors.append(f"{path}: {spec['document_type']} has no field {field!r}")


def from_page(page) -> dict:
	"""The compact form of a Studio Page, as save_studio_page takes it."""
	blocks = json.loads(page.draft_blocks or page.blocks or "[]")
	root = blocks[0] if blocks else {}
	variables = {row.variable_name: variable_value(row) for row in page.variables}
	spec = PageSpec(page.page_title, [], variables=variables)
	return {
		"blocks": [to_node(block, spec) for block in root.get("children", [])],
		"resources": {row.resource_name: resource_spec(row) for row in page.resources},
		"variables": variables,
		"script": page.script or "",
	}


def to_node(block: dict, spec: PageSpec) -> dict:
	name = block.get("componentName")
	if block.get("originalElement") == "div":
		name = CONTAINER
	node = {"name": name, "id": block.get("componentId")}
	style = dict(block.get("baseStyles") or {})
	if name == CONTAINER:
		for key, default in (("display", "flex"), ("flexDirection", "column")):
			if style.get(key) == default:
				style.pop(key)
	optional = {
		"label": block.get("blockName") if block.get("blockName") not in (None, name) else None,
		"props": {key: from_prop(value) for key, value in (block.get("componentProps") or {}).items()},
		"style": style,
		"tablet": block.get("tabletStyles"),
		"mobile": block.get("mobileStyles"),
		"children": [to_node(child, spec) for child in block.get("children") or []],
		"slots": {
			slot: [to_node(child, spec) for child in content.get("slotContent") or []]
			for slot, content in (block.get("componentSlots") or {}).items()
		},
		"events": {
			event: from_event(handler, spec) for event, handler in (block.get("componentEvents") or {}).items()
		},
		"visible": block.get("visibilityCondition"),
	}
	node.update({key: value for key, value in optional.items() if value})
	return node


def from_event(handler: dict, spec: PageSpec):
	"""The actions an event was saved from, unless its script was edited since."""
	actions = handler.get("actions")
	if actions and handler.get("script") == spec.compile(actions):
		return actions
	if handler.get("action") == "Run Script":
		return handler.get("script") or ""
	return handler


def to_prop(value):
	if isinstance(value, dict) and set(value) == {"$var"}:
		return {"$type": "variable", "name": value["$var"]}
	return value


def from_prop(value):
	if isinstance(value, dict) and value.get("$type") == "variable":
		return {"$var": value.get("name")}
	return value


def resource_spec(row) -> dict:
	spec = {}
	for key in sorted(RESOURCE_KEYS):
		value = row.get(key)
		if value in (None, "", "[]", "{}") or (key == "auto" and value):
			continue
		if key in ("fields", "filters", "params", "whitelisted_methods") and isinstance(value, str):
			value = json.loads(value)
		spec[key] = value
	if row.get("auto") == 0:
		spec["auto"] = False
	if row.resource_type == "Document" and spec.get("method") == "GET":
		spec.pop("method")
	return spec


def variable_row(name: str, value) -> dict:
	if isinstance(value, bool):
		return {"variable_name": name, "variable_type": "Boolean", "initial_value": "true" if value else "false"}
	if isinstance(value, int | float):
		return {"variable_name": name, "variable_type": "Number", "initial_value": json.dumps(value)}
	kind = "String" if isinstance(value, str) else "Object"
	return {"variable_name": name, "variable_type": kind, "initial_value": json.dumps(value)}


def variable_value(row):
	value = row.initial_value or ""
	if row.variable_type == "Boolean":
		return value == "true"
	try:
		return json.loads(value) if value else ("" if row.variable_type == "String" else None)
	except ValueError:
		return value


def empty_block(component_id: str, name: str) -> dict:
	return {
		"componentId": component_id,
		"componentName": name,
		"componentProps": {},
		"componentSlots": {},
		"componentEvents": {},
		"attributes": {},
		"children": [],
		"baseStyles": {},
		"mobileStyles": {},
		"tabletStyles": {},
		"classes": [],
	}


def new_id(name: str) -> str:
	return f"{name}-{''.join(random.choices(string.ascii_lowercase + string.digits, k=9))}"


def doctype_fields(doctype: str) -> set[str] | None:
	if not frappe.db.exists("DocType", doctype):
		return None  # reported on the resource
	meta = frappe.get_meta(doctype)
	return {field.fieldname for field in meta.fields} | set(default_fields) | {"name"}


def bindings(value) -> list[str]:
	"""The {{ }} expressions anywhere in a prop or action value."""
	if isinstance(value, str):
		return BINDING.findall(value)
	if isinstance(value, dict):
		return [expression for item in value.values() for expression in bindings(item)]
	if isinstance(value, list):
		return [expression for item in value for expression in bindings(item)]
	return []


def free_names(expression: str) -> set[str]:
	names = set()

	def collect(code: str) -> str:
		names.update(match.group(1) for match in IDENTIFIER.finditer(code) if not is_object_key(code, match.end()))
		return code

	map_code(expression, collect)
	return names


def local_names(expression: str) -> set[str]:
	"""Arrow function parameters, e.g. `row` in data.filter((row) => row.ok)."""
	names = set(re.findall(r"([A-Za-z_$][\w$]*)\s*=>", expression))
	for params in re.findall(r"\(([^()]*)\)\s*=>", expression):
		names.update(re.findall(r"[A-Za-z_$][\w$]*", params))
	return names


def map_code(expression: str, transform) -> str:
	"""Apply `transform` to the parts of a JS expression outside string literals."""
	out, last = [], 0
	for match in STRING_LITERAL.finditer(expression):
		out.append(transform(expression[last : match.start()]))
		out.append(match.group(0))
		last = match.end()
	out.append(transform(expression[last:]))
	return "".join(out)


def is_object_key(code: str, end: int) -> bool:
	"""`name: value` in an object literal. A ternary's `a ? b : c` also reads as one, so its
	middle name goes unchecked rather than flagged."""
	rest = code[end:].lstrip()
	return rest.startswith(":") and not rest.startswith("::")


def suggest(name: str, choices: set[str]) -> str:
	close = difflib.get_close_matches(name, sorted(choices), n=3)
	return f"; did you mean {', '.join(close)}?" if close else ""
