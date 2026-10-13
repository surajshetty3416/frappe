"""An Email Template drawn on the HTML canvas. Each save writes the block tree into the template's
`response_html` the way Gmail and Outlook render it: a 600px column of nested tables, every style
inline, flex rows as table cells, gaps as spacers and buttons as table cells around a link."""

import re
import frappe
from frappe import _
from frappe.utils import get_url

from frappe.web.ai.page_writer import kebab_to_camel
from frappe.web.output import label, load, prepared, walk

WIDTH = 600
BACKDROP = "#f4f4f5"

# what a table cell or a text element may carry inline; layout is the tables' job
BOX = {
	"background", "backgroundColor", "color", "padding", "paddingTop", "paddingRight", "paddingBottom",
	"paddingLeft", "border", "borderTop", "borderRight", "borderBottom", "borderLeft", "borderColor",
	"borderWidth", "borderStyle", "borderRadius", "fontFamily", "fontSize", "fontWeight", "fontStyle",
	"lineHeight", "letterSpacing", "textAlign", "textTransform", "textDecoration", "height", "minHeight",
}
TEXT_ELEMENTS = {"h1", "h2", "h3", "h4", "h5", "h6", "p", "span", "div", "label", "b", "strong", "em", "small"}
TABLE = 'role="presentation" cellpadding="0" cellspacing="0" border="0"'


def write(doc, method=None):
	"""before_validate: the template's HTML from the canvas, so the template validates it."""
	root = load(doc)
	if not root:
		return
	doc.use_html = 1
	doc.response_html = render(root)


def render(root: dict) -> str:
	root = prepared(root)
	styles = root.get("baseStyles") or {}
	backdrop = styles.get("--backdrop") or BACKDROP
	column = inline({key: value for key, value in styles.items() if key in BOX and not key.startswith("padding")})
	font = inline({key: styles[key] for key in ("fontFamily", "color") if styles.get(key)})
	padding = inline({key: value for key, value in styles.items() if key.startswith("padding")})
	return (
		f'<table {TABLE} width="100%" style="width:100%;background:{backdrop};{font}">'
		f'<tr><td align="center" style="padding:24px 12px;">'
		f'<table {TABLE} width="{WIDTH}" data-block-id="{root["blockId"]}" '
		f'style="width:100%;max-width:{WIDTH}px;border-collapse:separate;{column}">'
		f'<tr><td style="{padding}">{children(root)}</td></tr>'
		"</table></td></tr></table>"
	)


def block_html(block: dict, align: str | None) -> str:
	element = (block.get("element") or "div").lower()
	styles = block.get("baseStyles") or {}
	attrs = block.get("attributes") or {}
	block_id = block["blockId"]
	if element == "img":
		return image(block, attrs, styles, align)
	if element == "svg":
		return ""
	if element in ("a", "button") or (attrs.get("href") and not block.get("children")):
		return link(block, attrs, styles, align)
	if not block.get("children"):
		tag = element if element in TEXT_ELEMENTS - {"p", "span", "label"} else "div"
		text_styles = {"margin": "0", **{key: value for key, value in styles.items() if key in BOX}}
		return f'<{tag} data-block-id="{block_id}" style="{inline(text_styles)}">{block.get("innerHTML") or ""}</{tag}>'
	cell = inline({key: value for key, value in styles.items() if key in BOX})
	width = size(styles.get("width")) or size(styles.get("maxWidth"))
	table_align = f' align="{align}"' if align and width else ""
	return (
		f'<table {TABLE} width="{width or "100%"}"{table_align} data-block-id="{block_id}" '
		f'style="width:{css_width(width)};border-collapse:separate;"><tr>'
		f'<td valign="{valign(styles)}"{cell_align(styles)} style="{cell}">{children(block)}</td>'
		"</tr></table>"
	)


def children(block: dict) -> str:
	styles = block.get("baseStyles") or {}
	kids = [child for child in block.get("children") or [] if isinstance(child, dict)]
	align = {"center": "center", "flex-end": "right", "end": "right"}.get(styles.get("alignItems"))
	if is_row(styles):
		gap = px(styles.get("columnGap") or styles.get("gap"))
		cells = []
		for index, child in enumerate(kids):
			if index and gap:
				cells.append(f'<td width="{gap}" style="width:{gap}px;font-size:0;line-height:0;">&nbsp;</td>')
			child_width = size((child.get("baseStyles") or {}).get("width"))
			width = f' width="{child_width}"' if child_width else ""
			cells.append(f'<td valign="{valign(styles)}"{width}>{block_html(child, None)}</td>')
		justify = {"center": "center", "flex-end": "right", "end": "right"}.get(styles.get("justifyContent"))
		table_width = "" if justify else ' width="100%"'
		table_align = f' align="{justify}"' if justify else ""
		return f"<table {TABLE}{table_width}{table_align}><tr>{''.join(cells)}</tr></table>"
	gap = px(styles.get("rowGap") or styles.get("gap"))
	spacer = f'<div style="height:{gap}px;line-height:{gap}px;font-size:1px;">&nbsp;</div>' if gap else ""
	return spacer.join(block_html(child, align) for child in kids)


def link(block: dict, attrs: dict, styles: dict, align: str | None) -> str:
	href = absolute(attrs.get("href") or "#")
	text = block.get("innerHTML") or ""
	background = styles.get("background") or styles.get("backgroundColor")
	link_styles = {
		key: value
		for key, value in styles.items()
		if key in BOX and key not in ("background", "backgroundColor", "border", "borderRadius")
	}
	if not background:
		return f'<a href="{href}" data-block-id="{block["blockId"]}" style="{inline(link_styles)}">{text}</a>'
	radius = styles.get("borderRadius") or "0"
	cell = inline({"background": background, "borderRadius": radius, "border": styles.get("border")})
	anchor = inline({"display": "inline-block", "textDecoration": "none", "borderRadius": radius, **link_styles})
	table_align = f' align="{align}"' if align else ""
	return (
		f'<table {TABLE}{table_align}><tr><td bgcolor="{attr(background)}" style="{cell}">'
		f'<a href="{href}" data-block-id="{block["blockId"]}" style="{anchor}">{text}</a>'
		"</td></tr></table>"
	)


def image(block: dict, attrs: dict, styles: dict, align: str | None) -> str:
	width = size(styles.get("width")) or size(styles.get("maxWidth"))
	img_styles = inline(
		{"display": "block", "border": "0", "maxWidth": "100%", "height": "auto", "borderRadius": styles.get("borderRadius")}
	)
	width_attr = f' width="{width}"' if width and not width.endswith("%") else ""
	img = (
		f'<img src="{absolute(attrs.get("src") or "")}" alt="{attr(attrs.get("alt") or "")}"{width_attr} '
		f'data-block-id="{block["blockId"]}" style="{img_styles}">'
	)
	table_align = f' align="{align}"' if align else ""
	return f"<table {TABLE}{table_align}><tr><td>{img}</td></tr></table>"


def is_row(styles: dict) -> bool:
	return styles.get("display") in ("flex", "inline-flex") and styles.get("flexDirection", "row") in (
		"row",
		"row-reverse",
	)


def valign(styles: dict) -> str:
	if not is_row(styles):
		return "top"
	return {"center": "middle", "flex-end": "bottom", "end": "bottom"}.get(styles.get("alignItems"), "top")


def cell_align(styles: dict) -> str:
	align = styles.get("textAlign") or (
		{"center": "center", "flex-end": "right"}.get(styles.get("alignItems")) if not is_row(styles) else None
	)
	return f' align="{align}"' if align in ("left", "center", "right") else ""


def size(value) -> str | None:
	"""A width as a table attribute takes: pixels as a number, or a percentage."""
	value = str(value or "").strip()
	if match := re.fullmatch(r"(\d+(?:\.\d+)?)px", value):
		return str(round(float(match[1])))
	if re.fullmatch(r"\d+(?:\.\d+)?%", value):
		return value
	return None


def css_width(width: str | None) -> str:
	if not width:
		return "100%"
	return width if width.endswith("%") else f"{width}px"


def px(value) -> int:
	match = re.fullmatch(r"(\d+(?:\.\d+)?)(px)?", str(value or "").strip())
	return round(float(match[1])) if match else 0


def absolute(url: str) -> str:
	return (get_url(url) if url.startswith("/") else url).replace('"', "%22")


def attr(value) -> str:
	"""A value inside a double-quoted attribute; Jinja in it must stay readable to Jinja."""
	return str(value).replace('"', "'")


def inline(styles: dict) -> str:
	if (family := styles.get("fontFamily")) and "," not in str(family):
		# the canvas keeps one family; a mail client without it needs a fallback
		styles = {**styles, "fontFamily": f"{family}, Arial, sans-serif"}
	return "".join(
		f"{kebab(key)}:{attr(value)};"
		for key, value in styles.items()
		if value not in (None, "") and not key.startswith("--") and ":" not in key
	)


def kebab(key: str) -> str:
	return re.sub(r"[A-Z]", lambda match: f"-{match[0].lower()}", kebab_to_camel(key))


def problems(root: dict) -> list[str]:
	"""What an email client drops."""
	found = []
	for block in walk(root):
		styles = block.get("baseStyles") or {}
		if block.get("element") == "svg" or (block.get("customAttributes") or {}).get("data-lucide"):
			found.append(_("Block {0} is an icon. Email clients block SVG, so it is left out.").format(label(block)))
		if "qr_code(" in (block.get("innerHTML") or ""):
			found.append(_("Block {0} has a QR code. Gmail blocks its SVG image; put QR codes on a print format.").format(label(block)))
		if any("var(" in str(value) for value in styles.values()):
			found.append(_("Block {0} uses a CSS variable, which email clients ignore. Write the value.").format(label(block)))
		if styles.get("display") == "grid":
			found.append(_("Block {0} is a grid. Use display flex with a row direction for columns.").format(label(block)))
	return found


def render_for(doc, doctype: str, record: str) -> dict:
	"""The subject and message as the framework renders them for a record."""
	context = frappe.get_doc(doctype, record).as_dict()
	email = doc.get_formatted_email(context)
	return {"subject": email["subject"], "html": email["message"], "to": recipient(doctype, context)}


def recipient(doctype: str, values: dict) -> str | None:
	"""The record's email address, labelled with the person it belongs to, as a sender would
	address it: `speaker_name` labels `speaker_email`, and only a plain `email` takes the title."""
	meta = frappe.get_meta(doctype)
	field = next((df.fieldname for df in meta.fields if df.fieldtype == "Data" and df.options == "Email"), None)
	field = field if values.get(field) else ("email" if values.get("email") else "email_id")
	address = values.get(field)
	if not address:
		return None
	if field in ("email", "email_id"):
		label = values.get(meta.get_title_field())
	else:
		label = values.get(field.removesuffix("email") + "name") if field.endswith("_email") else None
	return f"{label} <{address}>" if label and label != address and label != values.get("name") else address


@frappe.whitelist()
def senders() -> dict[str, list[str]]:
	"""Each template's automations, as when they send it: {"Registration Confirmed": ["Sent when an Attendee is created"]}."""
	from frappe.agents.api import trigger_words

	sent: dict[str, list[str]] = {}
	actions = frappe.get_all(
		"Automation Action",
		filters={"parenttype": "Automation Flow", "action_type": "SendNotification"},
		fields=["parent", "params"],
	)
	for action in actions:
		template = (frappe.parse_json(action.params) or {}).get("email_template")
		if not template or not frappe.has_permission("Automation Flow", "read", action.parent):
			continue
		flow = frappe.get_doc("Automation Flow", action.parent)
		if not flow.enabled:
			continue
		words = trigger_words(flow)
		sent.setdefault(template, []).append(f"Sent {words[0].lower()}{words[1:]}")
	return sent


@frappe.whitelist()
def send_test(template: str, record: str | None = None) -> str:
	"""Queue the template, rendered against a record, to the signed-in user."""
	doc = frappe.get_doc("Email Template", template)
	doc.check_permission("read")
	doctype = doc.reference_doctype
	context = frappe.get_doc(doctype, record).as_dict() if doctype and record else {}
	email = doc.get_formatted_email(context)
	recipient = frappe.db.get_value("User", frappe.session.user, "email") or frappe.session.user
	frappe.sendmail(
		recipients=[recipient],
		subject=email["subject"],
		message=email["message"],
		reference_doctype=doctype if record else "Email Template",
		reference_name=record or template,
	)
	return recipient
