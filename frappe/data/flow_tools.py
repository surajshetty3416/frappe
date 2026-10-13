"""Tools that let the AI layer (flow) fill the site's DocTypes. Listed under the `flow_tools` hook,
so every flow agent can attach them."""

from typing import Annotated, Any

import frappe
from frappe import _
from frappe.ai import artifacts, tool
from frappe.ai.lib.tool import ToolContext
from frappe.data.generator import MAX_COUNT, Generator

GENERATE_GUIDE = f"""Generate and insert many realistic records from a spec: you describe the data, the server makes it. Use it for demo data, prose included, and anything over about 20 records. Up to {MAX_COUNT} per call; all or nothing.

Load the Data skill before the first call. Its Kinds section lists every param each kind takes, and a param it does not list fails the call, so never call this to find out what a kind takes.

`fields` maps each fieldname to a spec {{"kind": ..., params}}, or to a bare value for a constant. Kinds: name, first_name, last_name, company, email, phone, date, datetime, int, float, choice, link, text, constant, fake, table. Every spec also takes `empty` (share left blank, 0 to 1) and `unique` (true).

`given` holds exact {{field: value}} records, dealt one per record in order. `count` always equals the number of given records, in a preview too: to preview a few, send those few given records and their count. A given key is a field of the DocType, or a fact a text template reads as {{key}}.

With `preview` true it inserts nothing: it checks the spec, makes every record, validates them, and returns five samples, the number of distinct values and the fewest and most words per text field. Preview instead of inserting test records.

For values that depend on a group (prices per ticket type, a date curve per period, wording per track), make one call per group with constants for the group.

Returns the count made, three sample records, and the DocType as an artifact."""

PREVIEW_SAMPLES = 5


@tool(
	description=GENERATE_GUIDE,
	requires_confirmation=True,
	confirm_prompt=lambda args: _("{0} {1} {2} records with {3}").format(
		_("Preview") if args.get("preview") else _("Generate"),
		args.get("count"),
		args.get("doctype"),
		", ".join(args.get("fields") or {}),
	),
)
def generate_records(
	doctype: Annotated[str, "The DocType to fill"],
	count: Annotated[int, f"How many records, 1 to {MAX_COUNT}"],
	fields: Annotated[dict[str, Any], "fieldname: spec"],
	given: Annotated[list[dict[str, Any]] | None, "Exact {field: value} records, one per generated record"] = None,
	seed: Annotated[int | None, "Repeat the same records with the same seed"] = None,
	preview: Annotated[bool, "Check the spec and return samples without inserting"] = False,
	*,
	ctx: ToolContext,
) -> dict:
	frappe.has_permission(doctype, "create", throw=True)
	gen = Generator(doctype, count, fields, seed, given)
	rows = gen.rows()
	if preview:
		for number, values in enumerate(rows, start=1):
			doc = frappe.new_doc(doctype)
			doc.update(values)
			try:
				doc.set("__islocal", True)
				doc._set_defaults()
				doc.set_docstatus()
				doc.check_if_latest()
				doc._validate_links()
				doc._validate()
			except Exception as e:
				frappe.throw(_("Record {0} of {1} is invalid: {2}").format(number, count, e))
		texts = [f for f, spec in gen.specs.items() if spec["kind"] == "text"]
		return {
			"doctype": doctype,
			"preview": True,
			"inserted": 0,
			"sample": rows[:PREVIEW_SAMPLES],
			"distinct": {f: len({str(r[f]) for r in rows}) for f in texts},
			"words": {f: [min(counts), max(counts)] for f in texts if (counts := [len(str(r[f] or "").split()) for r in rows])},
		}
	sample = []
	for number, values in enumerate(rows, start=1):
		doc = frappe.new_doc(doctype)
		doc.update(values)
		try:
			doc.insert()
		except Exception as e:
			frappe.throw(_("Record {0} of {1} failed, nothing was saved: {2}").format(number, count, e))
		if len(sample) < 3:
			sample.append({"name": doc.name, **values})
	# records are data, so the DocType shows as a card without the chat taking it over
	return {
		"doctype": doctype,
		"created": count,
		"sample": sample,
		"artifact": artifacts.describe("DocType", doctype),
	}
