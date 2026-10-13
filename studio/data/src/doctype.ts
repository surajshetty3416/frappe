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
		doctype.saving++
		try {
			const saved = await saveDocType(JSON.parse(JSON.stringify(doctype.doc)))
			if (doctype.name !== saved.name || !doctype.doc) return
			if (pending === 1) doctype.doc = saved
			else adoptNames(doctype.doc, saved)
		} catch (error) {
			toast.error(errorText(error))
			await open(doctype.name)
		} finally {
			pending--
			doctype.saving--
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

export function namingRule(doc: DocTypeDoc) {
	const rule = doc.autoname || ""
	if (rule.startsWith("field:")) return `From ${rule.slice(6)}`
	if (rule.startsWith("format:")) return `Series ${rule.slice(7)}`
	if (rule === "autoincrement") return "Number, counting up"
	if (rule === "Prompt") return "Typed in when created"
	if (!rule || rule === "hash") return "Random"
	return `Series ${rule}`
}

const capitalize = (text: string) => text[0].toUpperCase() + text.slice(1)
export const permissionSummary = (perm: DocTypeDoc["permissions"][number]) =>
	PERM_TYPES.filter((type) => perm[type])
		.map(capitalize)
		.join(", ") || "No access"

const SKIPPED = new Set(["owner", "creation", "modified", "modified_by", "docstatus", "idx", "parent", "parentfield", "parenttype"])
const ROW_SKIPPED = new Set([...SKIPPED, "name", "doctype"])

function compact(record: Record<string, unknown>, skipped: Set<string>) {
	return Object.fromEntries(
		Object.entries(record).filter(([key, value]) => !skipped.has(key) && !key.startsWith("_") && ![null, 0, ""].includes(value as never) && !(Array.isArray(value) && !value.length))
	)
}

// the DocType as its JSON file would hold it, without the bookkeeping and the empty values
export function docTypeJSON(doc: DocTypeDoc) {
	const out: Record<string, unknown> = compact(doc, SKIPPED)
	out.fields = doc.fields.map((field) => compact(field, ROW_SKIPPED))
	out.permissions = doc.permissions.map((perm) => compact(perm, ROW_SKIPPED))
	return JSON.stringify(out, null, 2)
}
