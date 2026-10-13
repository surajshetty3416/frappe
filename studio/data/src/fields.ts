import { dayjs } from "frappe-ui"

import type { DocField } from "./api"

const LAYOUT_TYPES = new Set(["Section Break", "Column Break", "Tab Break", "Fold", "Heading", "HTML", "Button", "Image"])
export const TABLE_TYPES = new Set(["Table", "Table MultiSelect"])

export const isLayout = (field: DocField) => LAYOUT_TYPES.has(field.fieldtype)
export const hasValue = (field: DocField) => !isLayout(field) && !TABLE_TYPES.has(field.fieldtype)

// the types a person picks for a field; layout types are the form's business, not the data's
export const fieldTypes = () => (window.field_types ?? ["Data", "Int", "Check", "Date", "Select", "Link"]).filter((type) => !LAYOUT_TYPES.has(type))

// what a field's `options` means for its type: the DocType it points to, or its choices
export function optionsKind(fieldtype: string): "doctype" | "table" | "choices" | null {
	if (fieldtype === "Link") return "doctype"
	if (TABLE_TYPES.has(fieldtype)) return "table"
	if (fieldtype === "Select") return "choices"
	return null
}

const ICONS: Record<string, string> = {
	Data: "lucide-type",
	"Small Text": "lucide-text",
	Text: "lucide-align-left",
	"Long Text": "lucide-align-left",
	"Text Editor": "lucide-file-text",
	"Markdown Editor": "lucide-file-text",
	"HTML Editor": "lucide-code-xml",
	Code: "lucide-code-xml",
	JSON: "lucide-braces",
	Int: "lucide-hash",
	Float: "lucide-hash",
	Percent: "lucide-percent",
	Currency: "lucide-banknote",
	Check: "lucide-square-check",
	Date: "lucide-calendar",
	Datetime: "lucide-calendar-clock",
	Time: "lucide-clock",
	Duration: "lucide-timer",
	Select: "lucide-list",
	Autocomplete: "lucide-list",
	Link: "lucide-link",
	"Dynamic Link": "lucide-link",
	Table: "lucide-table",
	"Table MultiSelect": "lucide-tags",
	Attach: "lucide-paperclip",
	"Attach Image": "lucide-image",
	Color: "lucide-palette",
	Rating: "lucide-star",
	Phone: "lucide-phone",
	Barcode: "lucide-qr-code",
	Password: "lucide-key-round",
	Signature: "lucide-signature",
	Geolocation: "lucide-map-pin",
	"Read Only": "lucide-lock",
	"Section Break": "lucide-separator-horizontal",
	"Column Break": "lucide-columns-2",
	"Tab Break": "lucide-panel-top",
}
export const fieldIcon = (fieldtype: string) => ICONS[fieldtype] ?? "lucide-type"

export const fieldLabel = (field: DocField) => field.label || field.fieldname || field.fieldtype

// dates read as Studio writes them elsewhere, "15 June 2027"; a time beside one shortens it, "20 Aug 2027, 16:17"
export const DATE_FORMATS: Record<string, string> = { Date: "D MMMM YYYY", Datetime: "D MMM YYYY, HH:mm" }

export function formatValue(field: DocField | undefined, value: unknown): string {
	if (value === null || value === undefined || value === "") return ""
	switch (field?.fieldtype) {
		case "Check":
			return value ? "Yes" : "No"
		case "Date":
		case "Datetime":
			return dayjs(String(value)).format(DATE_FORMATS[field.fieldtype])
		case "Currency":
		case "Float":
			return Number(value).toLocaleString(undefined, { maximumFractionDigits: 2 })
		case "Int":
			return Number(value).toLocaleString()
		default:
			return String(value)
	}
}
