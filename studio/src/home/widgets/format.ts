export interface FieldSpec {
	fieldname: string
	label: string
	fieldtype: string
	options?: string | null
	reqd?: 0 | 1
	read_only?: 0 | 1 | boolean
	default?: string | null
}

const NUMBERS = new Set(["Int", "Float", "Currency", "Percent"])

// a value as one line of a row
export function shown(field: FieldSpec, value: unknown) {
	if (value === null || value === undefined || value === "") return "—"
	if (field.fieldtype === "Check") return value ? field.label : `Not ${field.label.toLowerCase()}`
	if (NUMBERS.has(field.fieldtype)) return Number(value).toLocaleString()
	return String(value)
}

export function errorText(error: unknown) {
	const messages = (error as { messages?: string[] })?.messages
	const text = messages?.length ? messages[messages.length - 1] : (error as Error)?.message
	return (text || "Something went wrong.").replace(/<[^>]+>/g, "")
}
