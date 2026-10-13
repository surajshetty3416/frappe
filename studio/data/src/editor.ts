// A DocType in Studio's editor shell: its records, a form and its fields as the preview, and
// the shell's contract answered from the open DocType.
import { type ElementProperty, defineArtifactEditor } from "@shell/editor"
import { findTab } from "@shell/tabs"
import { toast } from "frappe-ui"

import { renameDocType } from "./api"
import DocTypePreview from "./components/DocTypePreview.vue"
import {
	docTypeJSON,
	doctype,
	editable,
	elementId,
	errorText,
	fieldOf,
	hasRecords,
	change,
	namingRule,
	open,
	permissionSummary,
	preview,
	titleFieldLabel,
} from "./doctype"
import { fieldIcon, fieldLabel, fieldTypes, optionsKind } from "./fields"
import { doctypeNames } from "./names"

const nodeOf = (id: string) => preview.host?.querySelector<HTMLElement>(`[data-element="${CSS.escape(id)}"]`) ?? null

const choices = (values: string[]) => values.map((value) => ({ label: value, value }))

function fieldProperties(id: string): ElementProperty[] {
	const field = fieldOf(id)
	if (!field || !editable.value) return []
	const set = (key: "fieldtype" | "reqd" | "options", value: unknown) =>
		change(() => Object.assign(field, { [key]: value }))
	const properties: ElementProperty[] = [
		{
			name: "fieldtype",
			label: "Type",
			icon: "lucide-shapes",
			type: "select",
			value: field.fieldtype,
			options: choices(fieldTypes()),
			set: (value) => set("fieldtype", value),
		},
		{
			name: "reqd",
			label: "Required",
			icon: "lucide-asterisk",
			type: "select",
			value: field.reqd ? "1" : "0",
			options: [
				{ label: "Required", value: "1" },
				{ label: "Optional", value: "0" },
			],
			set: (value) => set("reqd", Number(value)),
		},
	]
	const kind = optionsKind(field.fieldtype)
	if (kind === "doctype" || kind === "table") {
		const names = kind === "table" ? doctypeNames.tables : doctypeNames.links
		const value = field.options || ""
		properties.push({
			name: "options",
			label: kind === "table" ? "Rows of" : "Links to",
			icon: "lucide-arrow-right",
			type: "select",
			value,
			options: choices(value && !names.includes(value) ? [value, ...names] : names),
			set: (next) => set("options", next),
		})
	}
	return properties
}

export default defineArtifactEditor({
	preview: DocTypePreview,

	title: () => doctype.doc?.name ?? doctype.name,
	async rename(title) {
		const old = doctype.name
		try {
			const name = await renameDocType(old, title)
			const path = preview.router?.currentRoute.value.fullPath.replace(encodeURIComponent(old), encodeURIComponent(name)) ?? ""
			const tab = findTab("DocType", old)
			if (tab) Object.assign(tab, { name, title: name, path })
			await preview.router?.replace(path)
		} catch (error) {
			toast.error(errorText(error))
		}
	},
	status() {
		if (doctype.saving) return { label: "Saving…", theme: "gray" }
		if (doctype.doc && !doctype.doc.custom) return { label: "Core, read only", theme: "gray" }
		if (doctype.doc?.istable) return { label: "Child table", theme: "gray" }
		if (doctype.count === null) return { label: "Counting…", theme: "gray" }
		return { label: doctype.count === 1 ? "1 record" : `${doctype.count.toLocaleString()} records`, theme: "gray" }
	},
	primaryAction() {
		if (!editable.value || !hasRecords.value) return null
		return { label: "Demo data", icon: "lucide-sparkles", run: async () => void (doctype.demoData = true) }
	},
	details() {
		const doc = doctype.doc
		if (!doc) return []
		const permissions = doc.permissions.filter((perm) => !perm.permlevel)
		return [
			{ label: "Module", value: doc.module },
			{ label: "Naming", value: namingRule(doc) },
			{ label: "Title field", value: titleFieldLabel(doc) },
			{ label: "Track changes", value: doc.track_changes ? "On" : "Off" },
			{
				label: "Permissions",
				value: permissions.map((perm) => `${perm.role}: ${permissionSummary(perm)}`).join("; ") || "Nobody",
			},
		]
	},
	code: () => ({ language: "json", content: doctype.doc ? docTypeJSON(doctype.doc) : "" }),
	async reload(modified) {
		// the save this tab made itself
		if (doctype.saving || (modified && modified === doctype.doc?.modified)) return
		if (doctype.name) await open(doctype.name)
	},

	elementAt(node) {
		const element = node.closest<HTMLElement>("[data-element]")
		if (!element || !preview.host?.contains(element)) return null
		const field = fieldOf(element.dataset.element!)
		if (!field) return null
		return {
			id: elementId(field),
			label: fieldLabel(field),
			icon: fieldIcon(field.fieldtype),
			hasText: editable.value,
		}
	},
	elementRect: (id) => nodeOf(id)?.getBoundingClientRect() ?? null,
	textNode: (id) => nodeOf(id)?.querySelector<HTMLElement>("[data-text]") ?? null,
	setText(id, html) {
		const label = new DOMParser().parseFromString(html, "text/html").body.textContent?.trim()
		const field = fieldOf(id)
		if (field && label && label !== field.label) change(() => (field.label = label))
	},
	properties: fieldProperties,
})
