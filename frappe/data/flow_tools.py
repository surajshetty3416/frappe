"""Tools that let the AI layer (flow) fill the site's DocTypes. Listed under the `flow_tools` hook,
so every flow agent can attach them."""

from typing import Annotated, Any

import frappe
from frappe import _
from frappe.ai import tool
from frappe.ai.lib.tool import ToolContext
from frappe.ai.tools.builtins import _with_artifact
from frappe.data.generator import MAX_COUNT, Generator

GENERATE_GUIDE = f"""Generate and insert many realistic records from a spec: you describe the data, the server makes it. Use it for demo data and anything over about 20 records. Up to {MAX_COUNT} per call; all or nothing.

`fields` maps each fieldname to a spec {{"kind": ..., params}}, or to a bare value for a constant. Every spec also takes `empty` (share left blank, 0 to 1) and `unique` (true). Weighted options are a list (equal weights) or a {{value: weight}} map; a map gives exactly those proportions.

Kinds:
- name, first_name, last_name: one person per record, shared by these and email. `india` share of Indian names (default 1, the rest international), `women` share (default 0.5).
- company: `names` list or weight map; without it, made-up Indian company names, a `pool` of them, a few big.
- email: first.last at the domain of the record's company field (`company`: fieldname, default company), or a fixed `domain`; `free` share at gmail.com and similar.
- phone: `prefix` (default "+91 "), `digits` (10), `first` digits to start with ("987").
- date: `from`, `to` (YYYY-MM-DD, today, or -30d / +7d), or `ranges` [[from, to, weight], ...]; `skew` "rising", "falling" or -5 to 5 within each range; `weekdays` 7 weights Monday to Sunday.
- datetime: date params, plus `times` [["09:00", "09:30", weight], ...] for the time of day (default 09:00 to 18:00).
- int, float: `min`, `max`, `skew`; float takes `precision`.
- choice: `options` list or weight map. Select fields take only their options.
- link: an existing record of the Link field's DocType. `filters`, `weights` {{name: weight}}, `distribution` uniform or skewed (a few records get most), `unique` (each record once).
- text: `template`, or `templates` as a list or weight map. Placeholders: {{slot}} from `slots` {{slot: list or weight map}}, and a slot value may hold placeholders; {{field}} for another field of the record; {{link_field.field}} for a field of the linked record; {{person.first_name|last_name|full_name|country|he|she|his|her}}; {{0000}} a counter from `start` (default 1); {{10..90}} a number; {{code:6}} random capitals and digits.
- constant: `value`.
- fake: a Faker `method` with `args` and `locale` (default en_IN), e.g. city, street_address, sentence.
- table: child rows, `rows` (count or [min, max]) and `fields`, a spec for the child DocType.

For values that depend on a group (prices per ticket type, a date curve per period, wording per track), make one call per group with constants for the group.

Returns the count made, three sample records, and the DocType as an artifact."""


@tool(
	description=GENERATE_GUIDE,
	requires_confirmation=True,
	confirm_prompt=lambda args: _("Generate {0} {1} records with {2}").format(
		args.get("count"), args.get("doctype"), ", ".join(args.get("fields") or {})
	),
)
def generate_records(
	doctype: Annotated[str, "The DocType to fill"],
	count: Annotated[int, f"How many records, 1 to {MAX_COUNT}"],
	fields: Annotated[dict[str, Any], "fieldname: spec"],
	seed: Annotated[int | None, "Repeat the same records with the same seed"] = None,
	*,
	ctx: ToolContext,
) -> dict:
	frappe.has_permission(doctype, "create", throw=True)
	rows = Generator(doctype, count, fields, seed).rows()
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
	return _with_artifact({"doctype": doctype, "created": count, "sample": sample}, ctx, "DocType", [doctype])
