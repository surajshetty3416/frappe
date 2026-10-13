import { call } from "frappe-ui"

declare global {
	interface Window {
		field_types?: string[]
	}
}

export type Flag = 0 | 1

export interface DocField {
	name?: string
	fieldname?: string
	label?: string
	fieldtype: string
	options?: string | null
	reqd?: Flag
	in_list_view?: Flag
	read_only?: Flag
	hidden?: Flag
	idx?: number
	[key: string]: unknown
}

export const PERM_TYPES = ["read", "write", "create", "delete", "submit"] as const
export type PermType = (typeof PERM_TYPES)[number]

export interface DocPerm extends Partial<Record<PermType, Flag>> {
	name?: string
	role: string
	permlevel: number
	[key: string]: unknown
}

export interface DocTypeDoc {
	name: string
	module: string
	custom: Flag
	istable: Flag
	issingle: Flag
	is_submittable: Flag
	autoname?: string
	naming_rule?: string
	title_field?: string
	show_title_field_in_link?: Flag
	track_changes: Flag
	modified: string
	fields: DocField[]
	permissions: DocPerm[]
	[key: string]: unknown
}

export interface SchemaNode {
	name: string
	core: boolean
	istable: Flag
	count: number | null
	fields: Required<Pick<DocField, "fieldname" | "label" | "fieldtype" | "options" | "reqd">>[]
}

export type Row = Record<string, unknown> & { name: string }

export const getSchema = (): Promise<SchemaNode[]> => call("frappe.data.api.get_schema")

export const getDocType = (name: string): Promise<DocTypeDoc> => call("frappe.client.get", { doctype: "DocType", name })

export const saveDocType = (doc: DocTypeDoc): Promise<DocTypeDoc> => call("frappe.client.save", { doc })

export const renameDocType = (name: string, newName: string): Promise<string> =>
	call("frappe.client.rename_doc", { doctype: "DocType", old_name: name, new_name: newName })

export const getRecords = (doctype: string, fields: string[], limit = 100): Promise<Row[]> =>
	call("frappe.client.get_list", { doctype, fields, order_by: "modified desc", limit_page_length: limit })

export const getRecord = (doctype: string, name: string): Promise<Row> => call("frappe.client.get", { doctype, name })

// the titles of the records Link fields point to, keyed `doctype::name`, for DocTypes that show titles in links
export function getLinkTitles(fields: DocField[], rows: Row[]): Promise<Record<string, string>> {
	const links: Record<string, Set<string>> = {}
	for (const field of fields) {
		if (field.fieldtype !== "Link" || !field.options) continue
		for (const row of rows) {
			const value = row[field.fieldname!]
			if (value) (links[field.options] ||= new Set()).add(String(value))
		}
	}
	if (!Object.keys(links).length) return Promise.resolve({})
	return call("frappe.data.api.get_link_title_map", {
		links: Object.fromEntries(Object.entries(links).map(([doctype, names]) => [doctype, [...names]])),
	})
}

export const countRecords = (doctype: string): Promise<number> => call("frappe.client.get_count", { doctype })

export const setValues = (doctype: string, name: string, values: Record<string, unknown>): Promise<Row> =>
	call("frappe.client.set_value", { doctype, name, fieldname: values })

export const insertRecord = (doctype: string, values: Record<string, unknown>): Promise<Row> =>
	call("frappe.client.insert", { doc: { ...values, doctype } })

export const getNames = (doctype: string, filters: Record<string, unknown> = {}): Promise<string[]> =>
	call("frappe.client.get_list", { doctype, filters, fields: ["name"], order_by: "name asc", limit_page_length: 0 }).then((rows) =>
		(rows as Row[]).map((row) => row.name)
	)
