"""Tools that let the AI layer (flow) fill the site's DocTypes. Listed under the `flow_tools` hook,
so every flow agent can attach them."""

from typing import Annotated, Any

import frappe
from frappe import _
from frappe.ai import artifacts, tool
from frappe.ai.lib.tool import ToolContext
from frappe.data.generator import MAX_COUNT, Generator

GENERATE_GUIDE = f"""Generate and insert many realistic records from a spec: you describe the data, the server makes it. Use it for demo data, prose included, and anything over about 20 records. Up to {MAX_COUNT} per call; all or nothing. With `preview` true it inserts nothing: it checks the spec, makes every record, validates them, and returns five samples, the number of distinct values and the fewest and most words per text field. Preview instead of inserting test records.

`fields` maps each fieldname to a spec {{"kind": ..., params}}, or to a bare value for a constant. Every spec also takes `empty` (share left blank, 0 to 1) and `unique` (true). Weighted options are a list (equal weights) or a {{value: weight}} map; a map gives exactly those proportions.

`given` holds the exact values the data must have, as {{field: value}} records dealt one per record in order; count equals their number. Exact titles with their track and format, or 40 named people, go here, never into records you write. The specs generate every other field around them, and a spec fills a field a given record leaves out. A given name is the record's person, so email follows it. Templates read a given value as {{key}}; a key that is not a field is a fact for templates only, such as the product a given title is about.

Kinds:
- name, first_name, last_name: one person per record, shared by these and email. `india` share of Indian names (default 1, the rest international), `women` share (default 0.5).
- company: `names` list or weight map; without it, made-up Indian company names, a `pool` of them, a few big.
- email: first.last of the record's person at the domain of its company field (`company`: fieldname, default company), or a fixed `domain`; `free` share at gmail.com and similar. Unique by default, also against existing records: a taken address gets a number. Make emails with this kind, not a text template, which cannot number a taken address.
- phone: `prefix` (default "+91 "), `digits` (10), `first` digits to start with ("987"). Unique by default, also against existing records.
- date: `from`, `to` (YYYY-MM-DD, today, or -30d / +7d), or `ranges` [[from, to, weight], ...]; `skew` "rising", "falling" or -5 to 5 within each range; `weekdays` 7 weights Monday to Sunday.
- datetime: date params, plus `times` [["09:00", "09:30", weight], ...] for the time of day (default 09:00 to 18:00).
- int, float: `min`, `max`, `skew`; float takes `precision`.
- choice: `options` list or weight map. Select fields take only their options. `pick` [min, max] draws that many different options per record, joined by ", ", such as 2 to 4 tags.
- link: an existing record of the Link field's DocType. `filters`, `weights` {{name: weight}}, `distribution` uniform or skewed (a few records get most), `unique` (each record at most once), `each` (every matching record exactly once, oldest first, so count equals their number: one accepted talk per speaker).
- text: `template`, or `templates` as a list or weight map. `words` [min, max]: the text is redrawn until its word count is in the range. Placeholders: {{slot}} from `slots` {{slot: list or weight map}}; {{field}} for another field or a given value of the record; {{link_field.field}} for a field of the linked record; {{person.first_name|last_name|full_name|country}} and pronouns {{person.he|his|him}} (she, her, her for women), capitalised as {{person.He|His|Him}}; {{0000}} a counter from `start` (default 1); {{10..90}} a number; {{code:6}} random capitals and digits.
  A slot is drawn once per record and shared by every text field of the record, so give each slot in one field only. A slot value may hold placeholders. A slot value may be an object, read as {{slot.key}}, to keep facts together: a topic's product, result and tags in the title, the abstract and the tags field. Text can fill Link and Select fields too, such as "track": "{{topic.track}}".
- constant: `value`.
- fake: a Faker `method` with `args` and `locale` (default en_IN), e.g. city, street_address, sentence.
- table: child rows, `rows` (count or [min, max]) and `fields`, a spec for the child DocType.

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
