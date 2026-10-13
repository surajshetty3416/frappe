import frappe
from frappe import _
from frappe.automation_engine.actions.base import get_action_registry
from frappe.automation_engine.api import run_manually

RUN = "Automation Run"
DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
DOC_EVENTS = {
	"Doc Created": "created",
	"Doc Updated": "updated",
	"Doc Deleted": "deleted",
	"Doc Submitted": "submitted",
	"Doc Cancelled": "cancelled",
}


@frappe.whitelist()
def get_home() -> dict:
	"""The site's own agents and every automation, each described in words."""
	frappe.has_permission("Flow Agent", "read", throw=True)
	agents = frappe.get_list(
		"Flow Agent",
		filters={"is_system_generated": 0},
		fields=["name", "title", "description", "model", "enabled", "modified"],
		order_by="modified desc",
	)
	tools = frappe.get_all(
		"Flow Agent Tool",
		filters={"parenttype": "Flow Agent", "parent": ("in", [agent.name for agent in agents] or [""])},
		pluck="parent",
	)
	for agent in agents:
		agent.tools = tools.count(agent.name)

	automations = []
	for name in frappe.get_list("Automation Flow", pluck="name", order_by="modified desc"):
		flow = frappe.get_doc("Automation Flow", name)
		last = frappe.get_all(
			RUN, filters={"automation": name}, fields=["status", "started_at"], order_by="creation desc", limit=1
		)
		automations.append(
			{
				"name": name,
				"title": flow.title,
				"enabled": flow.enabled,
				"trigger": trigger_words(flow),
				"does": action_words(flow),
				"last_run": last[0] if last else None,
				"modified": flow.modified,
			}
		)
	return {"agents": agents, "automations": automations}


@frappe.whitelist()
def get_flow(name: str) -> dict:
	"""An automation as the preview draws it: its trigger, conditions and steps in words."""
	flow = frappe.get_doc("Automation Flow", name)
	flow.check_permission("read")
	return {
		"doc": flow.as_dict(convert_dates_to_str=True),
		"trigger": trigger_words(flow),
		"conditions": filter_words(flow.document_type, frappe.parse_json(flow.filters) if flow.filters else []),
		"condition": flow.condition,
		"steps": [step_card(row.as_dict()) for row in flow.actions],
	}


@frappe.whitelist()
def get_runs(automation: str, limit: int = 30) -> list[dict]:
	frappe.has_permission("Automation Flow", "read", automation, throw=True)
	return frappe.get_all(
		RUN,
		filters={"automation": automation},
		fields=["name", "status", "started_at", "ended_at", "reference_doctype", "reference_name", "error_summary"],
		order_by="creation desc",
		limit=int(limit),
	)


@frappe.whitelist()
def get_run(name: str) -> dict:
	"""A run's steps; a Run Agent step carries its agent's reply, or the session it runs in."""
	run = frappe.get_doc(RUN, name)
	frappe.has_permission("Automation Flow", "read", run.automation, throw=True)
	planned = {step.get("step_key"): step for step in frappe.parse_json(run.actions_snapshot) or []}
	steps = []
	for row in run.steps:
		output = frappe.parse_json(row.output) if row.output else {}
		step = {
			"idx": row.step_idx,
			"label": action_label(row.action_type),
			"action_type": row.action_type,
			"status": row.status,
			"duration_ms": row.duration_ms,
			"detail": row.detail,
			"message": row.message,
		}
		if row.action_type == "RunAgent":
			params = frappe.parse_json(planned.get(row.step_key, {}).get("params")) or {}
			step["agent"] = params.get("agent")
			reference = (output or {}).get("destination_reference") or {}
			if reference.get("name"):
				step["agent_run"] = frappe.db.get_value(
					"Flow Run", reference["name"], ["name", "status", "output", "error", "session"], as_dict=True
				)
		steps.append(step)
	return {
		"name": run.name,
		"status": run.status,
		"started_at": run.started_at,
		"ended_at": run.ended_at,
		"reference_doctype": run.reference_doctype,
		"reference_name": run.reference_name,
		"error_summary": run.error_summary,
		"steps": steps,
	}


@frappe.whitelist(methods=["POST"])
def run_now(automation: str) -> dict:
	"""Run the automation once, on the newest record of its DocType when it watches one."""
	document_type = frappe.db.get_value("Automation Flow", automation, "document_type")
	docname = None
	if document_type:
		newest = frappe.get_list(document_type, pluck="name", order_by="creation desc", limit=1)
		if not newest:
			frappe.throw(_("There is no {0} to run it on yet.").format(document_type))
		docname = newest[0]
	run_manually(automation, docname)
	return {"document": docname}


def article(word: str) -> str:
	return "an" if word[:1].lower() in "aeiou" else "a"


def field_label(doctype: str | None, fieldname: str | None) -> str:
	if not (doctype and fieldname):
		return fieldname or ""
	return frappe.get_meta(doctype).get_label(fieldname) or fieldname


def trigger_words(flow) -> str:
	doctype, kind = flow.document_type or "", flow.trigger_type
	if kind in DOC_EVENTS:
		return f"When {article(doctype)} {doctype} is {DOC_EVENTS[kind]}"
	if kind == "Field Value Changed":
		words = f"When {field_label(doctype, flow.trigger_field)} of {article(doctype)} {doctype} changes"
		if flow.from_value:
			words += f" from {flow.from_value}"
		if flow.to_value:
			words += f" to {flow.to_value}"
		return words
	if kind == "Date Based":
		label = field_label(doctype, flow.date_field)
		days = abs(flow.date_offset or 0)
		if not days:
			return f"On the {label} of each {doctype}"
		return f"{days} day{'s' if days != 1 else ''} {(flow.date_direction or 'after').lower()} the {label} of each {doctype}"
	if kind == "Scheduled":
		return schedule_words(flow.cron_expression or "")
	if kind == "Custom Event":
		return f"When {flow.custom_event} happens"
	return "When someone runs it"


def schedule_words(cron: str) -> str:
	parts = cron.split()
	if len(parts) != 5:
		return f"On the schedule {cron}"
	minute, hour, day, month, weekday = parts
	at = f"{int(hour):02}:{int(minute):02}" if hour.isdigit() and minute.isdigit() else None
	if month == "*" and day == "*":
		if at and weekday == "*":
			return f"Every day at {at}"
		if at and weekday in ("1-5", "MON-FRI"):
			return f"Every weekday at {at}"
		if at and weekday.isdigit():
			return f"Every {DAYS[int(weekday) % 7]} at {at}"
		if hour == "*" and weekday == "*":
			if minute.isdigit():
				return f"Every hour at :{int(minute):02}"
			if minute.startswith("*/"):
				return f"Every {minute[2:]} minutes"
			if minute == "*":
				return "Every minute"
	if at and month == "*" and weekday == "*" and day.isdigit():
		return f"Every month on day {day} at {at}"
	return f"On the schedule {cron}"


def filter_words(doctype: str | None, filters) -> list[str]:
	words = []
	for item in filters or []:
		if isinstance(item, str):
			words.append(item)
		elif item and isinstance(item[0], list):
			words.append("(" + " ".join(filter_words(doctype, item)) + ")")
		elif len(item) >= 3:
			words.append(f"{field_label(doctype, item[0])} {item[1]} {item[2]}")
	return words


def action_label(action_type: str | None) -> str:
	action = get_action_registry().get(action_type or "")
	return action.label if action else (action_type or "")


def step_card(row: dict) -> dict:
	params = frappe.parse_json(row.get("params")) or {}
	kind = row.get("step_type") or "Action"
	card = {
		"idx": row.get("idx"),
		"kind": kind,
		"action_type": row.get("action_type"),
		"parent_step": row.get("parent_step"),
		"branch": row.get("branch"),
	}
	if kind == "Wait":
		return {**card, "label": f"Wait {params.get('value')} {(params.get('unit') or '').lower()}"}
	if kind == "WaitForEvent":
		return {**card, "label": "Wait for an event", "detail": params.get("event")}
	if kind == "If":
		return {**card, "label": "If", "detail": row.get("step_condition")}
	card["label"] = action_label(row.get("action_type"))
	if row.get("action_type") == "RunAgent":
		agent = params.get("agent")
		card["agent"] = agent
		card["agent_title"] = frappe.db.get_value("Flow Agent", agent, "title") if agent else None
		card["prompt"] = params.get("prompt")
		return card
	action = get_action_registry().get(row.get("action_type") or "")
	labels = {field["fieldname"]: field.get("label") for field in (action.params_schema if action else [])}
	card["params"] = [
		{"label": labels.get(key) or key, "value": value if isinstance(value, str) else frappe.as_json(value)}
		for key, value in params.items()
		if value not in (None, "", [], {})
	]
	return card


def action_words(flow) -> str:
	words = []
	for row in flow.actions:
		if (row.step_type or "Action") != "Action":
			continue
		if row.action_type == "RunAgent":
			agent = (frappe.parse_json(row.params) or {}).get("agent")
			words.append(f"Runs {frappe.db.get_value('Flow Agent', agent, 'title') or agent}")
		else:
			words.append(action_label(row.action_type))
	return ", then ".join(words) or "Does nothing yet"
