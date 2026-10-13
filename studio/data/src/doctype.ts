// The open DocType: what the preview's views and the shell's editor contract both read.
import { toast } from "frappe-ui"
import { computed, reactive } from "vue"
import type { Router } from "vue-router"

import { type DocField, type DocTypeDoc, PERM_TYPES, countRecords, getDocType, saveDocType } from "./api"

export const doctype = reactive({
	name: "",
	doc: null as DocTypeDoc | null,
	loading: false,
	error: "",
	saving: 0,
	// a save finished a moment ago
	saved: false,
	count: null as number | null,
	demoData: false,
})

// set by the preview: where the shell finds the elements it selects, and the router it navigates with
export const preview: { host: HTMLElement | null; router: Router | null } = { host: null, router: null }

// core DocTypes belong to the framework; Studio shows them and changes only the site's own
export const editable = computed(() => Boolean(doctype.doc?.custom))
export const hasRecords = computed(() => Boolean(doctype.doc && !doctype.doc.istable && !doctype.doc.issingle))

export const errorText = (error: unknown) => {
	const messages = (error as { messages?: string[] })?.messages
	const text = messages?.length ? messages.join(" ") : (error as Error)?.message
	return (text || "That did not work").replace(/<[^>]+>/g, "")
}

export async function open(name: string) {
	doctype.name = name
	doctype.loading = true
	doctype.error = ""
	try {
		const doc = await getDocType(name)
		if (doctype.name !== name) return
		doctype.doc = doc
		refreshCount()
	} catch (error) {
		if (doctype.name !== name) return
		doctype.doc = null
		doctype.error = errorText(error)
	} finally {
		if (doctype.name === name) doctype.loading = false
	}
}

export async function refreshCount() {
	const name = doctype.name
	const count = hasRecords.value ? await countRecords(name).catch(() => null) : null
	if (doctype.name === name) doctype.count = count
}

let savedTimer = 0
export async function saving<T>(work: () => Promise<T>) {
	doctype.saving++
	doctype.saved = false
	try {
		const result = await work()
		if (doctype.saving === 1) {
			doctype.saved = true
			clearTimeout(savedTimer)
			savedTimer = window.setTimeout(() => (doctype.saved = false), 2000)
		}
		return result
	} finally {
		doctype.saving--
	}
}

// Each change applies at once and saves in order, each save carrying every change made so far.
let queue: Promise<void> = Promise.resolve()
let pending = 0

export function change(mutate: (doc: DocTypeDoc) => void) {
	const doc = doctype.doc
	if (!doc || !editable.value) return queue
	mutate(doc)
	doc.fields.forEach((field, index) => (field.idx = index + 1))
	doc.permissions.forEach((perm, index) => (perm.idx = index + 1))
	pending++
	queue = queue.then(async () => {
		try {
			const saved = await saving(() => saveDocType(JSON.parse(JSON.stringify(doctype.doc))))
			if (doctype.name !== saved.name || !doctype.doc) return
			if (pending === 1) doctype.doc = saved
			else adoptNames(doctype.doc, saved)
		} catch (error) {
			toast.error(errorText(error))
			await open(doctype.name)
		} finally {
			pending--
		}
	})
	return queue
}

// a later change is still waiting: keep it, and take what the server gave the rows it saved
function adoptNames(local: DocTypeDoc, saved: DocTypeDoc) {
	local.modified = saved.modified
	for (const key of ["fields", "permissions"] as const) {
		local[key].forEach((row, index) => {
			const match = saved[key][index]
			if (!row.name && match) Object.assign(row, { name: match.name, fieldname: (match as DocField).fieldname ?? row.fieldname })
		})
	}
}

export const elementId = (field: DocField) => `field:${field.fieldname}`
export const fieldOf = (id: string) => doctype.doc?.fields.find((field) => elementId(field) === id) ?? null

const labelOf = (doc: DocTypeDoc, fieldname: string) => {
	const field = doc.fields.find((field) => field.fieldname === fieldname)
	return field?.label || fieldname
}

// how a record gets its ID, shown as the first ID it gives
export function namingRule(doc: DocTypeDoc) {
	const rule = doc.autoname || ""
	if (rule.startsWith("field:")) return `From ${labelOf(doc, rule.slice(6))}`
	if (rule.startsWith("format:")) return firstOfSeries(rule.slice(7).replace(/\{(#+)\}/g, ".$1"))
	if (rule === "autoincrement") return "1, 2, 3…"
	if (rule === "Prompt") return "Typed in when created"
	if (!rule || rule === "hash") return "Random"
	return firstOfSeries(rule)
}
const firstOfSeries = (series: string) => series.replace(/\.?(#+)/g, (_, hashes: string) => "1".padStart(hashes.length, "0")).replace(/\.$/, "")

export const titleFieldLabel = (doc: DocTypeDoc) => (doc.title_field ? labelOf(doc, doc.title_field) : "None")

export const permissionSummary = (perm: DocTypeDoc["permissions"][number]) =>
	PERM_TYPES.filter((type) => perm[type])
		.join(", ") || "no access"

const FIELD_KEYS = ["fieldname", "label", "fieldtype", "options", "reqd", "unique", "default", "in_list_view", "hidden", "read_only", "description"]
const PERM_KEYS = ["role", "permlevel", ...PERM_TYPES]

const pick = (row: Record<string, unknown>, keys: string[]) =>
	Object.fromEntries(keys.filter((key) => ![null, undefined, 0, ""].includes(row[key] as never)).map((key) => [key, row[key]]))

// the DocType as someone exports it: what it is called, how it names its records, its fields and who can use it
export function docTypeJSON(doc: DocTypeDoc) {
	const out = {
		...pick(doc, ["name", "module", "autoname", "title_field", "istable", "issingle", "is_submittable"]),
		fields: doc.fields.map((field) => pick(field, FIELD_KEYS)),
		permissions: doc.permissions.map((perm) => pick(perm, PERM_KEYS)),
	}
	return JSON.stringify(out, null, 2)
}
