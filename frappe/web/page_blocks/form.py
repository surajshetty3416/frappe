"""The form block: fields of one DocType that a site visitor fills in to insert a document."""

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import cint, flt, getdate, strip_html, validate_email_address

from frappe.web.page_blocks import esc, published_block

INPUT_TYPES = {
	"Data": "text",
	"Int": "number",
	"Float": "number",
	"Currency": "number",
	"Percent": "number",
	"Date": "date",
	"Datetime": "datetime-local",
	"Time": "time",
}
DATA_INPUT_TYPES = {"Email": "email", "Phone": "tel", "URL": "url"}
TEXT_AREAS = {"Small Text", "Text", "Long Text", "Text Editor", "Markdown Editor"}
SUPPORTED = set(INPUT_TYPES) | TEXT_AREAS | {"Select", "Link", "Check"}
NUMBERS = {"Int", "Float", "Currency", "Percent"}
LINK_OPTION_LIMIT = 200
TEXT_LIMIT = 10000
# a form never inserts the framework's own DocTypes, whoever vouches for it
BLOCKED_MODULES = {"Core", "Custom", "Desk", "Email", "Integrations", "Website"}
SAVEPOINT = "form_block"
GUEST_EXTRA_RIGHTS = ("read", "write", "delete")
DEFAULT_SUCCESS = "Thank you. We have received your submission."


class FormBlock:
	key = "form"

	def __init__(self, config: dict):
		self.config = config
		doctype = config.get("doctype")
		if not doctype or not frappe.db.exists("DocType", doctype):
			frappe.throw(_("The form's DocType {0} does not exist.").format(doctype))
		self.meta = frappe.get_meta(doctype)
		self.fields = [df for name in config.get("fields") or [] if (df := self.meta.get_field(name))]

	@classmethod
	def clean(cls, config: dict) -> dict:
		"""The config with defaults, or an error that tells the agent what to fix."""
		config = {
			"doctype": config.get("doctype"),
			"fields": list(config.get("fields") or []),
			"submit_label": config.get("submit_label") or _("Submit"),
			"success_message": config.get("success_message") or _(DEFAULT_SUCCESS),
			"success_route": config.get("success_route") or "",
			"allow_guest": cint(config.get("allow_guest")),
		}
		block = cls(config)
		block.check_doctype()
		block.check_fields()
		if config["success_route"] and not config["success_route"].startswith("/"):
			frappe.throw(_("success_route must be a path on this site, starting with /."))
		block.check_guest_can_submit()
		return config

	def check_doctype(self):
		if self.meta.istable or self.meta.issingle or self.meta.is_virtual:
			frappe.throw(
				_(
					"A form inserts documents, so {0} cannot be a child table, single or virtual DocType."
				).format(self.meta.name)
			)
		if self.blocked():
			frappe.throw(
				_("A form cannot insert {0}, a {1} DocType.").format(self.meta.name, self.meta.module)
			)

	def blocked(self) -> bool:
		return not self.meta.custom and self.meta.module in BLOCKED_MODULES

	def check_fields(self):
		names = self.config["fields"]
		if not names:
			frappe.throw(_("A form needs at least one field."))
		unknown = [name for name in names if not self.meta.get_field(name)]
		if unknown:
			frappe.throw(_("{0} has no fields {1}.").format(self.meta.name, ", ".join(unknown)))
		unsupported = [
			f"{df.fieldname} ({df.fieldtype})" for df in self.fields if df.fieldtype not in SUPPORTED
		]
		if unsupported:
			frappe.throw(_("A form cannot show {0}.").format(", ".join(unsupported)))

	def check_guest_can_submit(self):
		if frappe.has_permission(self.meta.name, "create", user="Guest"):
			return
		if not self.config["allow_guest"]:
			frappe.throw(
				_(
					"Guests cannot create {0}. Give Guest create permission on it, or allow guest submissions on the form."
				).format(self.meta.name)
			)
		frappe.has_permission(self.meta.name, "create", throw=True)

	def warnings(self) -> list[str]:
		"""What would make the form fail or leak, for the agent to fix."""
		doctype, warnings = self.meta.name, []
		shown = set(self.config["fields"])
		if missing := [
			df.fieldname
			for df in self.meta.fields
			if df.reqd and df.fieldname not in shown and not df.default and df.fieldtype in SUPPORTED
		]:
			warnings.append(
				_(
					"{0} requires {1}, which the form leaves out. A submission fails unless the server fills them."
				).format(doctype, ", ".join(missing))
			)
		# a permission row's checkboxes default to on, so "Guest may create" often grants more
		if extra := [
			ptype for ptype in GUEST_EXTRA_RIGHTS if frappe.has_permission(doctype, ptype, user="Guest")
		]:
			warnings.append(
				_(
					"Guest may also {0} {1}, so any visitor can do that to every record through the API. Give Guest create only."
				).format(", ".join(extra), doctype)
			)
		return warnings

	# --- render ---

	def render(self, block_id: str) -> str:
		fields = "".join(self.field_html(df, block_id) for df in self.fields)
		return (
			f'<form class="fb-form" novalidate data-fb-form data-page="{{{{ page_name }}}}" data-block="{esc(block_id)}">'
			f'<div class="fb-form-fields">{fields}</div>'
			'<div class="fb-honeypot" aria-hidden="true"><label>Company website'
			'<input type="text" name="company_website" tabindex="-1" autocomplete="off"></label></div>'
			'<p class="fb-form-error" role="alert" hidden></p>'
			f'<button class="fb-submit" type="submit">{esc(self.config.get("submit_label") or _("Submit"))}</button>'
			"</form>"
			'<div class="fb-form-success" role="status" tabindex="-1" hidden>'
			f"<p>{esc(self.config.get('success_message') or _(DEFAULT_SUCCESS))}</p></div>"
		)

	def field_html(self, df, block_id: str) -> str:
		input_id = esc(f"fb-{block_id}-{df.fieldname}")
		help_text = f'<p class="fb-help">{esc(df.description)}</p>' if df.description else ""
		error = '<p class="fb-error" hidden></p>'
		wide = " fb-field-wide" if df.fieldtype in TEXT_AREAS or df.fieldtype == "Check" else ""
		if df.fieldtype == "Check":
			checked = " checked" if cint(df.default) else ""
			control = (
				f'<label class="fb-check"><input id="{input_id}" type="checkbox" name="{esc(df.fieldname)}"{checked}>'
				f"<span>{esc(_(df.label))}</span></label>"
			)
			return f'<div class="fb-field{wide}" data-field="{esc(df.fieldname)}">{control}{help_text}{error}</div>'
		required = '<span class="fb-required" aria-hidden="true">*</span>' if df.reqd else ""
		label = f'<label class="fb-label" for="{input_id}">{esc(_(df.label))}{required}</label>'
		control = self.control_html(df, input_id)
		return f'<div class="fb-field{wide}" data-field="{esc(df.fieldname)}">{label}{control}{help_text}{error}</div>'

	def control_html(self, df, input_id: str) -> str:
		attrs = f'id="{input_id}" name="{esc(df.fieldname)}" class="fb-input"' + (
			" required" if df.reqd else ""
		)
		if df.fieldtype in TEXT_AREAS:
			return f'<textarea {attrs} rows="5" maxlength="{TEXT_LIMIT}">{esc(df.default)}</textarea>'
		if df.fieldtype in ("Select", "Link"):
			options = "".join(
				f'<option value="{esc(value)}"{" selected" if value == df.default else ""}>{esc(label)}</option>'
				for value, label in self.choices(df)
			)
			placeholder = "" if df.default else f'<option value="">{esc(_("Select"))}</option>'
			return f"<select {attrs}>{placeholder}{options}</select>"
		input_type = (
			DATA_INPUT_TYPES.get(df.options, "text") if df.fieldtype == "Data" else INPUT_TYPES[df.fieldtype]
		)
		extra = ""
		if df.fieldtype == "Data":
			extra = f' maxlength="{cint(df.length) or 140}"'
		elif df.fieldtype in NUMBERS:
			extra = ' step="1"' if df.fieldtype == "Int" else ' step="any"'
		autocomplete = {"email": "email", "tel": "tel", "url": "url"}.get(input_type)
		if autocomplete:
			extra += f' autocomplete="{autocomplete}"'
		value = (
			f' value="{esc(df.default)}"' if df.default and df.fieldtype not in ("Date", "Datetime") else ""
		)
		return f'<input type="{input_type}" {attrs}{extra}{value}>'

	def choices(self, df) -> list[tuple[str, str]]:
		if df.fieldtype == "Select":
			return [(option, _(option)) for option in (df.options or "").split("\n") if option]
		target = frappe.get_meta(df.options)
		title_field = target.title_field if target.show_title_field_in_link else None
		fields = ["name", title_field] if title_field else ["name"]
		rows = frappe.get_all(df.options, fields=fields, order_by="name asc", limit=LINK_OPTION_LIMIT)
		return [(row.name, row.get(title_field) or row.name if title_field else row.name) for row in rows]

	# --- submit ---

	def submit(self, values: dict, vouched_by: str) -> dict:
		ignore_permissions = self.insert_permission(vouched_by)
		doc_values, errors = self.read_values(values)
		if errors:
			return {"ok": False, "errors": errors}
		doc = frappe.new_doc(self.meta.name)
		doc.update(doc_values)
		frappe.db.savepoint(SAVEPOINT)
		try:
			doc.insert(ignore_permissions=ignore_permissions)
		except frappe.ValidationError as exc:
			frappe.db.rollback(save_point=SAVEPOINT)
			frappe.local.message_log = []
			return {
				"ok": False,
				"message": strip_html(str(exc)) or _("We could not save this. Check the form and try again."),
			}
		return {"ok": True, "route": self.config.get("success_route") or None}

	def insert_permission(self, vouched_by: str) -> bool:
		"""Whether the insert skips permissions: only for a form that allows guests, on a page
		last saved by someone who may create the DocType."""
		if self.blocked():
			raise frappe.PermissionError(_("This form does not take submissions."))
		if frappe.has_permission(self.meta.name, "create"):
			return False
		if self.config.get("allow_guest") and frappe.has_permission(
			self.meta.name, "create", user=vouched_by
		):
			return True
		raise frappe.PermissionError(_("This form does not take submissions."))

	def read_values(self, values: dict) -> tuple[dict, dict]:
		doc_values, errors = {}, {}
		for df in self.fields:
			try:
				value = self.read_value(df, values.get(df.fieldname))
			except ValueError as exc:
				errors[df.fieldname] = str(exc)
				continue
			if df.reqd and value in (None, ""):
				errors[df.fieldname] = _("{0} is required.").format(_(df.label))
			elif value is not None:
				doc_values[df.fieldname] = value
		return doc_values, errors

	def read_value(self, df, raw):
		value = raw.strip() if isinstance(raw, str) else raw
		if df.fieldtype == "Check":
			return 1 if value in (True, 1, "1", "on", "true") else 0
		if value in (None, ""):
			return None
		if not isinstance(value, str | int | float):
			raise ValueError(_("Enter a valid value."))
		value = str(value)
		if df.fieldtype in NUMBERS:
			return read_number(df, value)
		if df.fieldtype in ("Date", "Datetime", "Time"):
			return read_date(df, value)
		if df.fieldtype == "Select" and value not in (df.options or "").split("\n"):
			raise ValueError(_("Choose one of the options."))
		if df.fieldtype == "Link" and not frappe.db.exists(df.options, value):
			raise ValueError(_("Choose one of the options."))
		if df.fieldtype == "Data" and df.options == "Email" and not validate_email_address(value):
			raise ValueError(_("Enter a valid email address."))
		limit = (cint(df.length) or 140) if df.fieldtype == "Data" else TEXT_LIMIT
		if len(value) > limit:
			raise ValueError(_("Use at most {0} characters.").format(limit))
		return value


def read_number(df, value: str):
	try:
		return int(value) if df.fieldtype == "Int" else flt(float(value))
	except ValueError:
		raise ValueError(_("Enter a number.")) from None


def read_date(df, value: str):
	if df.fieldtype == "Time":
		return value
	try:
		getdate(value)
	except Exception:
		raise ValueError(_("Enter a valid date.")) from None
	return value.replace("T", " ")


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=10, seconds=10 * 60)
def submit(page: str, block: str, values: dict | str, company_website: str | None = None) -> dict:
	"""Insert the document a visitor filled in. A filled honeypot gets a quiet success."""
	if company_website:
		return {"ok": True, "route": None}
	row, config = published_block(page, block, FormBlock.key)
	return FormBlock(config).submit(frappe.parse_json(values) or {}, vouched_by=row.modified_by)
