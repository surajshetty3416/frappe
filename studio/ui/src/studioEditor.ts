// Studio App in Studio's editor shell: the open page as the preview, and the shell's contract
// answered from the app editor's stores.
import { defineArtifactEditor, type ElementProperty } from "@shell/editor"
import { computed } from "vue"

import AppDetails from "@ui/components/AppDetails.vue"
import BlockDetails from "@ui/components/BlockDetails.vue"
import ListColumns from "@ui/components/ListColumns.vue"
import PageCode from "@ui/components/PageCode.vue"
import StudioToolbar from "@ui/components/StudioToolbar.vue"
import StudioPage from "@ui/pages/StudioPage.vue"
import Block, { type styleProperty } from "@ui/utils/block"
import useCanvasStore from "@ui/stores/canvasStore"
import useStudioStore from "@ui/stores/studioStore"
import { getBlockCopyWithoutParent, jsToJson } from "@ui/utils/serializer"

const canvas = () => useCanvasStore().activeCanvas
const host = () => canvas()?.canvasContainer as HTMLElement | null | undefined

// a block repeated by its parent (a list's rows) renders once per item; an element past the first
// copy adds which copy it is to the block's id, which the agent reads
const elementId = (componentId: string, copy: number) => (copy ? `${componentId}#${copy}` : componentId)
const parseId = (id: string) => {
	const [componentId, copy] = id.split("#")
	return { componentId, copy: Number(copy ?? 0) }
}
// the preview shows one breakpoint at a time, and slot content always reports itself as desktop
const copiesOf = (componentId: string) =>
	Array.from(
		host()?.querySelectorAll<HTMLElement>(`.__studio_component__[data-component-id="${CSS.escape(componentId)}"]`) ?? [],
	)
const nodeOf = (id: string) => {
	const { componentId, copy } = parseId(id)
	return copiesOf(componentId)[copy] ?? null
}
const blockOf = (id: string) => (canvas()?.findBlock(parseId(id).componentId) as Block | null) ?? null

const ICONS: Record<string, string> = {
	TextBlock: "lucide-type",
	Header: "lucide-heading-1",
	Button: "lucide-square-mouse-pointer",
	List: "lucide-list",
	ListHeader: "lucide-columns-3",
	ListHeaderCell: "lucide-columns-3",
	ListRows: "lucide-rows-3",
	ListRow: "lucide-rows-3",
	ListCell: "lucide-columns-3",
	Avatar: "lucide-user",
	ImageView: "lucide-image",
	container: "lucide-frame",
}
function kind(block: Block) {
	if (block.isRoot()) return { label: "Page", icon: "lucide-file" }
	const name = block.componentName
	const title = Block.getComponents()?.[name]?.title
	return {
		label: block.blockName && block.blockName !== name ? block.blockName : title || (name === "container" ? "Container" : name),
		icon: ICONS[name] ?? "lucide-box",
	}
}

// only literal text edits in place; a bound value ({{ item.name }}) is the agent's, and an icon
// button shows no label
const TEXT_PROP: Record<string, string> = { TextBlock: "text", Header: "text", Button: "label" }
function textProp(block: Block) {
	const prop = TEXT_PROP[block.componentName]
	if (block.componentName === "Button" && block.getProp("icon")) return null
	const value = prop ? block.getProp(prop) : null
	return typeof value === "string" && !value.includes("{{") ? prop : null
}

// A block stretched by its parent, such as a list in a full-height row, shows no more than its
// content: the outline ends where its children end, unless it paints a background or border.
function contentRect(node: HTMLElement | null) {
	if (!node) return null
	const rect = node.getBoundingClientRect()
	const children = Array.from(node.children).map((child) => child.getBoundingClientRect()).filter((child) => child.height)
	const style = getComputedStyle(node)
	const painted = style.backgroundColor !== "rgba(0, 0, 0, 0)" || parseFloat(style.borderBottomWidth) > 0
	if (!children.length || painted) return rect
	const bottom = Math.max(...children.map((child) => child.bottom)) + parseFloat(style.paddingBottom)
	return bottom < rect.bottom ? new DOMRect(rect.x, rect.y, rect.width, bottom - rect.y) : rect
}

const RESIZABLE = new Set(["ImageView", "Avatar", "Card"])

// Select has no empty value, so "none" stands for an unset one
const NONE = "none"
const options = (values: (string | number)[], label = (value: string) => value) =>
	values.map((value) => ({ label: label(String(value)), value: String(value) }))
const px = (values: number[]) => values.map((value) => ({ label: `${value}`, value: `${value}px` }))
const SPACING = px([0, 4, 8, 12, 16, 24, 32, 48])

// a value outside the list still shows, as itself
const withValue = (list: { label: string; value: string }[], value: string) =>
	value && !list.some((option) => option.value === value) ? [{ label: value, value }, ...list] : list

function style(block: Block, name: string, label: string, icon: string, type: "color" | "select", list?: { label: string; value: string }[], fallback = ""): ElementProperty {
	let value = String(block.getStyle(name as styleProperty) ?? "")
	if (!value && type === "color") value = String(block.getRenderedStyle(name as styleProperty) ?? "")
	value ||= fallback
	return {
		name,
		label,
		icon,
		type,
		value,
		options: list && withValue(list, value),
		set: (next) => block.setStyle(name as styleProperty, next === NONE ? null : next),
	}
}

function prop(block: Block, name: string, label: string, icon: string, list: { label: string; value: string }[], fallback: string): ElementProperty {
	const raw = block.getProp(name)
	const value = raw === undefined || raw === null || raw === "" ? fallback : String(raw)
	return {
		name,
		label,
		icon,
		type: "select",
		value,
		options: withValue(list, value),
		set(next) {
			if (next === NONE) block.removeProp(name)
			else if (next === "true" || next === "false") block.setProp(name, next === "true")
			else block.setProp(name, next)
		},
	}
}

// frappe-ui's text sets weights between the named ones, such as 420 for regular
function nearestWeight(block: Block) {
	const weight = Number(block.getRenderedStyle("fontWeight" as styleProperty)) || 400
	return String([400, 500, 600, 700].reduce((best, next) => (Math.abs(next - weight) < Math.abs(best - weight) ? next : best)))
}

const YES_NO = [
	{ label: "Yes", value: "true" },
	{ label: "No", value: "false" },
]

function blockProperties(block: Block): ElementProperty[] {
	switch (block.componentName) {
		case "TextBlock":
		case "Header":
			return [
				prop(block, "fontSize", "Size", "lucide-baseline", FONT_SIZES, "text-base"),
				style(block, "fontWeight", "Weight", "lucide-bold", "select", [
					{ label: "Regular", value: "400" },
					{ label: "Medium", value: "500" },
					{ label: "Semibold", value: "600" },
					{ label: "Bold", value: "700" },
				], nearestWeight(block)),
				style(block, "color", "Color", "lucide-palette", "color"),
				style(block, "textAlign", "Align", "lucide-align-left", "select", options(["left", "center", "right"], capitalize), "left"),
			]
		case "Button":
			return [
				prop(block, "variant", "Variant", "lucide-square-mouse-pointer", options(["solid", "subtle", "outline", "ghost"], capitalize), "subtle"),
				prop(block, "icon", "Icon", "lucide-sparkles", [{ label: "None", value: NONE }, ...options(BUTTON_ICONS, (value) => value.replace("lucide-", ""))], NONE),
				prop(block, "size", "Size", "lucide-baseline", [
					{ label: "Small", value: "sm" },
					{ label: "Medium", value: "md" },
					{ label: "Large", value: "lg" },
					{ label: "XL", value: "xl" },
				], "sm"),
			]
		case "List":
			return [
				listColumns(block),
				prop(block, "rowHeight", "Row height", "lucide-rows-3", options([40, 48, 56, 64, 72]), "40"),
				prop(block, "selectable", "Selectable", "lucide-list-checks", YES_NO, "false"),
				prop(block, "divider", "Divider", "lucide-separator-horizontal", options(["inset", "full", "none"], capitalize), "inset"),
			]
		case "ImageView":
		case "Avatar":
			return [
				{
					name: "image",
					label: "Upload image",
					icon: "lucide-image-up",
					type: "upload",
					accept: "image/*",
					value: String(block.getProp("image") ?? ""),
					set: (url) => block.setProp("image", url),
				},
				{
					name: "image_url",
					label: "Image address",
					icon: "lucide-link",
					type: "text",
					placeholder: "https://",
					value: String(block.getProp("image") ?? ""),
					set: (url) => (url ? block.setProp("image", url) : block.removeProp("image")),
				},
				visible(block),
			]
		default:
			return [
				style(block, "width", "Width", "lucide-maximize-2", "select", [{ label: "Auto", value: NONE }, ...options(["25%", "50%", "75%", "100%"])], NONE),
				style(block, "padding", "Padding", "lucide-frame", "select", SPACING),
				style(block, "gap", "Gap", "lucide-columns-3", "select", SPACING),
				visible(block),
			]
	}
}

const FONT_SIZES = [
	{ label: "Extra small", value: "text-xs" },
	{ label: "Small", value: "text-sm" },
	{ label: "Base", value: "text-base" },
	{ label: "Large", value: "text-lg" },
	{ label: "XL", value: "text-xl" },
	{ label: "2XL", value: "text-2xl" },
	{ label: "3XL", value: "text-3xl" },
	{ label: "4XL", value: "text-4xl" },
]

const BUTTON_ICONS = ["lucide-plus", "lucide-check", "lucide-x", "lucide-pencil", "lucide-trash-2", "lucide-search", "lucide-download", "lucide-external-link", "lucide-arrow-right", "lucide-star"]

function listColumns(block: Block): ElementProperty {
	const columns = block.getProp("columns")
	const count = Array.isArray(columns) ? columns.length : 0
	return {
		name: "columns",
		label: "Columns",
		icon: "lucide-columns-3",
		type: "popover",
		value: count === 1 ? "1 column" : `${count} columns`,
		component: { component: ListColumns, props: { block } },
		set: () => {},
	}
}

// the block's v-if: always, never, or the binding the agent wrote, shown as itself
function visible(block: Block): ElementProperty {
	const value = block.visibilityCondition || "always"
	return {
		name: "visibilityCondition",
		label: "Visible",
		icon: "lucide-eye",
		type: "select",
		value,
		options: withValue(
			[
				{ label: "Always", value: "always" },
				{ label: "Never", value: "false" },
			],
			value,
		),
		set: (next) => (block.visibilityCondition = next === "always" ? undefined : next),
	}
}

const capitalize = (value: string) => value.charAt(0).toUpperCase() + value.slice(1)

const app = computed(() => useStudioStore().activeApp)
const siteURL = () => (import.meta.env.DEV ? window.site_url : "")

function publishState() {
	const store = useStudioStore()
	const pages = Object.values(store.appPages)
	if (!pages.some((page) => page.published)) return "draft"
	const changed = store.activePage?.draft_blocks || pages.some((page) => !page.published)
	return changed ? "changed" : "published"
}

export default defineArtifactEditor({
	preview: StudioPage,

	title: () => app.value?.app_title || "Untitled app",
	rename: (title) => useStudioStore().updateActiveApp("app_title", title),
	saving: () => useStudioStore().savingPage,
	status() {
		const state = publishState()
		if (state === "draft") return { label: "Draft", theme: "gray" }
		if (state === "changed") return { label: "Unpublished changes", theme: "orange" }
		return { label: "Published", theme: "green" }
	},
	primaryAction() {
		const store = useStudioStore()
		const live = publishState() === "published"
		return {
			label: live ? "Published" : "Publish",
			icon: live ? "lucide-check" : undefined,
			disabled: live || !store.activeApp || store.savingPage,
			// publishApp reports its own success and failure
			run: () => store.publishApp() ?? Promise.resolve(),
		}
	},
	details() {
		const store = useStudioStore()
		if (!app.value) return []
		const address = `/${app.value.route}`
		const home = app.value.app_home ? store.appPages[app.value.app_home]?.page_title : null
		const rows = [
			{ label: "Address", value: address, href: publishState() === "draft" ? undefined : `${siteURL()}${address}` },
			{ label: "Pages", value: String(Object.keys(store.appPages).length) },
		]
		if (home) rows.push({ label: "Home", value: home })
		if (store.activePage) rows.push({ label: "Page route", value: store.activePage.route })
		return rows
	},
	code() {
		const root = canvas()?.getRootBlock()
		return { language: "json", content: root ? jsToJson(getBlockCopyWithoutParent(root)) : "" }
	},
	// the selected block's props, styles and events, or the app's and the page's settings
	detailsForm: () => ({ component: canvas()?.selectedBlocks[0] ? BlockDetails : AppDetails }),
	barControls: () => ({ component: StudioToolbar }),
	codeTabs: () =>
		(["Page", "Script", "Data"] as const).map((part) => ({
			name: part,
			label: part,
			component: { component: PageCode, props: { part } },
		})),
	async reload(modified) {
		const store = useStudioStore()
		if (!store.activeApp || (modified && modified === store.activeApp.modified)) return
		await store.setApp(store.activeApp.name)
		if (store.selectedPage) await store.setPage(store.selectedPage)
	},

	elementAt(node) {
		const element = node.closest<HTMLElement>(".__studio_component__[data-component-id]")
		if (!element || !host()?.contains(element)) return null
		const componentId = element.dataset.componentId as string
		const block = canvas()?.findBlock(componentId) as Block | null
		if (!block) return null
		const { label, icon } = kind(block)
		const copy = Math.max(0, copiesOf(componentId).indexOf(element))
		return { id: elementId(componentId, copy), label, icon, hasText: Boolean(textProp(block)) }
	},
	elementRect: (id) => contentRect(nodeOf(id)),
	textNode(id) {
		const node = nodeOf(id)
		if (!node) return null
		return blockOf(id)?.componentName === "Button" ? node.querySelector<HTMLElement>("span.truncate") : node
	},
	setText(id, html) {
		const block = blockOf(id)
		const name = block && textProp(block)
		if (!name) return
		const text = document.createElement("div")
		text.innerHTML = html
		block.setProp(name, text.textContent?.trim() ?? "")
	},
	properties(id) {
		const block = blockOf(id)
		return block ? blockProperties(block) : []
	},

	select(id) {
		const block = id ? blockOf(id) : null
		if (block) canvas()?.selectBlockById(block.componentId)
		else canvas()?.clearSelection()
	},
	actions(id) {
		const block = blockOf(id)
		if (!block || block.isRoot()) return []
		return [
			{ name: "duplicate", label: "Duplicate", icon: "lucide-copy", run: () => block.duplicateBlock() },
			{ name: "delete", label: "Delete", icon: "lucide-trash-2", run: () => canvas()?.removeBlock(block) },
		]
	},
	resizable(id) {
		const block = blockOf(id)
		return Boolean(block && !block.isRoot() && (block.isContainer() || RESIZABLE.has(block.componentName)))
	},
	resize(id, size) {
		const block = blockOf(id)
		// the preview may be scaled to fit the panel
		const scale = canvas()?.canvasProps.scale || 1
		if (!block) return
		block.setStyle("width" as styleProperty, `${Math.round(size.width / scale)}px`)
		block.setStyle("height" as styleProperty, `${Math.round(size.height / scale)}px`)
	},
	undo() {
		const history = canvas()?.history
		if (history?.canUndo()) history.undo()
	},
	redo() {
		const history = canvas()?.history
		if (history?.canRedo()) history.redo()
	},
})
