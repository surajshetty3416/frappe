// A print format or an email template on the HTML canvas. Both keep a Builder block tree in
// `canvas_blocks`; the server renders it through the framework's own print view or email path,
// and the preview shows that output against a record, so what the editor shows is what prints
// or sends. Selection, text edits and properties change the tree, and a save renders it again.
import {
	type ArtifactAction,
	type ArtifactCode,
	type ArtifactDetail,
	type ArtifactStatus,
	type ElementProperty,
	defineArtifactEditor,
} from "@shell/editor"
import { useDebounceFn } from "@vueuse/core"
import { call, toast } from "frappe-ui"
import { defineComponent, h, reactive, watch } from "vue"
import { useRoute, useRouter } from "vue-router"

import OutputPreview from "./OutputPreview.vue"

export type OutputDoctype = "Print Format" | "Email Template"

export interface CanvasBlock {
	blockId: string
	element?: string
	blockName?: string
	innerHTML?: string
	baseStyles?: Record<string, string>
	attributes?: Record<string, string>
	customAttributes?: Record<string, string>
	children?: CanvasBlock[]
}

export interface Page {
	size: string
	width: number
	height: number
	margins: { top: number; right: number; bottom: number; left: number }
}

export interface OutputDoc {
	name: string
	modified: string
	canvas_blocks?: string | null
	[key: string]: unknown
}

export interface OutputState {
	doctype: OutputDoctype
	name: string
	doc: OutputDoc | null
	tree: CanvasBlock | null
	record: string | null
	target: string | null
	records: { name: string; title?: string }[]
	html: string
	subject: string
	page: Page | null
	error: string
	loading: boolean
	saving: boolean
	host: HTMLElement | null
}

interface OutputSpec {
	doctype: OutputDoctype
	param: string
	route: (name: string) => string
	status: (state: OutputState) => ArtifactStatus
	primaryAction: (state: OutputState) => ArtifactAction | null
	details: (state: OutputState) => ArtifactDetail[]
	code: (state: OutputState) => ArtifactCode
}

const walk = (block: CanvasBlock): CanvasBlock[] => [block, ...(block.children ?? []).flatMap(walk)]
const JINJA = /\{\{|\{%/
const DEFAULT_NAMES = new Set(["body", "div", "container", "text", "section", "p", "span", "a", "img"])

function kind(block: CanvasBlock, root: boolean) {
	const element = block.element ?? "div"
	if (root) return { label: "Page", icon: "lucide-file" }
	if (block.innerHTML?.includes("qr_code(")) return { label: "QR code", icon: "lucide-qr-code" }
	if (element === "img") return { label: "Image", icon: "lucide-image" }
	if (element === "a" || element === "button") return { label: "Button", icon: "lucide-mouse-pointer-click" }
	if (/^h[1-6]$/.test(element)) return { label: "Heading", icon: "lucide-heading" }
	if (!block.children?.length) return { label: "Text", icon: "lucide-type" }
	return { label: "Container", icon: "lucide-square-dashed" }
}

export function defineOutputEditor(spec: OutputSpec) {
	const state = reactive<OutputState>({
		doctype: spec.doctype,
		name: "",
		doc: null,
		tree: null,
		record: null,
		target: null,
		records: [],
		html: "",
		subject: "",
		page: null,
		error: "",
		loading: false,
		saving: false,
		host: null,
	})

	const findBlock = (id: string) => (state.tree ? walk(state.tree).find((block) => block.blockId === id) ?? null : null)
	const nodeOf = (id: string) => state.host?.querySelector<HTMLElement>(`[data-block-id="${CSS.escape(id)}"]`) ?? null
	const editable = (block: CanvasBlock | null) =>
		Boolean(block && block !== state.tree && !block.children?.length && block.element !== "img" && !JINJA.test(block.innerHTML ?? ""))

	async function render() {
		if (!state.name) return
		const result = await call("frappe.web.output.preview", { doctype: spec.doctype, name: state.name, record: state.record })
		state.html = result.html ?? ""
		state.subject = result.subject ?? ""
		state.page = result.page ?? null
		state.error = result.error ?? ""
		state.target = result.doctype ?? null
		state.record = result.record ?? state.record
	}

	async function load(name: string) {
		state.loading = true
		try {
			const doc = (await call("frappe.client.get", { doctype: spec.doctype, name })) as OutputDoc
			if (name !== state.name) return
			state.doc = doc
			try {
				const parsed = JSON.parse(doc.canvas_blocks || "null")
				state.tree = Array.isArray(parsed) ? parsed[0] ?? null : parsed
			} catch {
				state.tree = null
			}
			await render()
			state.records = await call("frappe.web.output.records", { doctype: spec.doctype, name })
		} finally {
			if (name === state.name) state.loading = false
		}
	}

	async function persist() {
		if (!state.tree || !state.name) return
		state.saving = true
		try {
			const doc = (await call("frappe.client.set_value", {
				doctype: spec.doctype,
				name: state.name,
				fieldname: "canvas_blocks",
				value: JSON.stringify(state.tree),
			})) as OutputDoc
			state.doc = doc
			await render()
		} catch (error) {
			toast.error((error as Error)?.message || "Could not save")
		} finally {
			state.saving = false
		}
	}
	const save = useDebounceFn(persist, 300)

	const Preview = defineComponent({
		name: "OutputPreviewRoute",
		setup() {
			const route = useRoute()
			const router = useRouter()
			watch(
				() => [route.params[spec.param], route.params.record] as const,
				([name, record]) => {
					if (typeof name !== "string" || !name) return
					const recordName = typeof record === "string" && record ? record : null
					if (name !== state.name) {
						state.name = name
						state.record = recordName
						state.doc = null
						state.html = ""
						load(name)
					} else if (recordName && recordName !== state.record) {
						state.record = recordName
						render()
					}
				},
				{ immediate: true },
			)
			// the record is in the path: a link to an artifact keeps its path, and the chat adds its own query
			const pick = (record: string) => router.replace({ params: { ...route.params, record }, query: route.query })
			return () =>
				h(OutputPreview, {
					state,
					onPick: pick,
					onHost: (node: HTMLElement | null) => (state.host = node),
				})
		},
	})

	function textAlign(block: CanvasBlock): ElementProperty {
		const options = ["left", "center", "right"].map((value) => ({ label: value[0].toUpperCase() + value.slice(1), value }))
		const node = nodeOf(block.blockId)
		const current = block.baseStyles?.textAlign || (node ? getComputedStyle(node).textAlign : "left")
		return {
			name: "align",
			label: "Align",
			icon: "lucide-align-left",
			type: "select",
			value: current === "start" ? "left" : current,
			options,
			set(value) {
				block.baseStyles = { ...block.baseStyles, textAlign: value }
				save()
			},
		}
	}

	function color(block: CanvasBlock, key: "color" | "background", label: string): ElementProperty {
		return {
			name: key,
			label,
			icon: key === "color" ? "lucide-baseline" : "lucide-paint-bucket",
			type: "color",
			value: block.baseStyles?.[key] ?? "",
			set(value) {
				block.baseStyles = { ...block.baseStyles, [key]: value }
				save()
			},
		}
	}

	return defineArtifactEditor({
		preview: Preview,
		title: () => (state.doc?.name === state.name ? state.name : ""),
		async rename(title) {
			const name = await call("frappe.client.rename_doc", { doctype: spec.doctype, old_name: state.name, new_name: title })
			state.name = name
			window.history.replaceState(window.history.state, "", spec.route(name))
			await load(name)
		},
		status: () => (state.saving ? { label: "Saving…", theme: "gray" } : spec.status(state)),
		primaryAction: () => spec.primaryAction(state),
		details: () => (state.doc ? spec.details(state) : []),
		code: () => spec.code(state),
		async reload(modified) {
			if (!state.name) return
			if (modified && modified === state.doc?.modified) return
			await load(state.name)
		},

		elementAt(node) {
			const element = node.closest<HTMLElement>("[data-block-id]")
			if (!element || !state.host?.contains(element)) return null
			const block = findBlock(element.dataset.blockId as string)
			if (!block) return null
			const { label, icon } = kind(block, block === state.tree)
			const name = block.blockName && !DEFAULT_NAMES.has(block.blockName) ? block.blockName : null
			return { id: block.blockId, label: name ?? label, icon, hasText: editable(block) }
		},
		elementRect: (id) => nodeOf(id)?.getBoundingClientRect() ?? null,
		textNode: (id) => (editable(findBlock(id)) ? nodeOf(id) : null),
		setText(id, html) {
			const block = findBlock(id)
			if (!block) return
			block.innerHTML = html
			save()
		},
		properties(id) {
			const block = findBlock(id)
			if (!block || block === state.tree) return []
			if (block.children?.length) return [color(block, "background", "Fill")]
			return [textAlign(block), color(block, "color", "Text color"), color(block, "background", "Fill")]
		},
	})
}
