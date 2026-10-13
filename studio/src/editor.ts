import { type Component, ref, shallowRef } from "vue"

// What a layer implements to open its artifact in the shell. The shell draws the tabs, the
// artifact bar, the context row under it, the drawers and the selection; the layer renders the preview and answers
// questions about it. Methods are read inside computeds, so reactive state they read updates the shell.
// The optional members are version 2: an editor without them keeps version 1's behaviour.
export interface ArtifactEditor {
	// the real output of the artifact the route names, filling the panel and nothing else
	preview: Component
	title(): string
	rename(title: string): Promise<unknown>
	// where the artifact stands: draft, published, a record count. Saving is `saving`, not a status
	status(): ArtifactStatus
	// a save is on its way; the bar shows a spinner beside its buttons
	saving?(): boolean
	primaryAction(): ArtifactAction | null
	// read-only rows in the Details drawer, under `detailsForm`
	details(): ArtifactDetail[]
	// read-only code, for an editor without `codeTabs`
	code(): ArtifactCode
	// someone else saved the artifact (the agent, a restore): show the saved state
	reload(modified?: string): Promise<unknown>

	// the element a node in the preview belongs to, for hover and selection
	elementAt(node: Element): PreviewElement | null
	// on screen now; it moves as the preview scrolls or zooms
	elementRect(id: string): DOMRect | null
	// the node holding the element's text, which the shell edits in place
	textNode(id: string): HTMLElement | null
	setText(id: string, html: string): void
	// at most four, on the context row while the element is selected
	properties(id: string): ElementProperty[]

	// the modes the artifact offers, the first one it opens in; both when absent. One mode hides the switch.
	modes?: EditorMode[]
	// the artifact's views, a switch on the context row
	views?(): ArtifactView[]
	// the layer's own controls on the context row, after the views
	barControls?(): LayerComponent | null
	// an editable form at the top of the Details drawer
	detailsForm?(): LayerComponent | null
	// the Code drawer, a tab per part; replaces `code`
	codeTabs?(): CodeTab[]
	// on the context row while the element is selected; "delete" also runs on Delete and Backspace, "duplicate" on Cmd+D
	actions?(id: string): ElementAction[]
	// the shell's selection changed
	select?(id: string | null): void
	// a drag on the selection's corner gives the element a new size, in pixels, when it ends
	resizable?(id: string): boolean
	resize?(id: string, size: { width: number; height: number }): void
	// Cmd+Z and Shift+Cmd+Z, from the layer's own history
	undo?(): void
	redo?(): void
}

export type EditorMode = "edit" | "preview"

// a layer's component and the props it mounts with
export interface LayerComponent {
	component: Component
	props?: Record<string, unknown>
}

export interface PreviewElement {
	id: string
	label: string
	icon: string
	hasText: boolean
}

export interface ElementProperty {
	name: string
	label: string
	icon: string
	// popover: the layer's `component` in a popover; upload: a file's URL; text: free-form
	type: "color" | "select" | "popover" | "upload" | "text"
	value: string
	options?: { label: string; value: string }[]
	component?: LayerComponent
	// upload: the file types, as an input's `accept` takes them
	accept?: string
	placeholder?: string
	set(value: string): void
}

export interface ElementAction {
	name: string
	label: string
	icon: string
	// an action that makes an element (duplicate) returns or resolves to its id, and the shell selects it
	run(): unknown
}

export interface ArtifactView {
	name: string
	label: string
	active: boolean
	open(): void
}

export interface CodeTab {
	name: string
	label: string
	component: LayerComponent
}

export interface ArtifactStatus {
	label: string
	theme: "gray" | "green" | "orange"
}

export interface ArtifactAction {
	label: string
	icon?: string
	disabled?: boolean
	run(): Promise<unknown>
}

export interface ArtifactDetail {
	label: string
	value: string
	href?: string
}

export interface ArtifactCode {
	language: string
	content: string
}

export const defineArtifactEditor = (editor: ArtifactEditor) => editor

// Edit selects in the preview; Preview lets clicks through to it
export const editorMode = ref<EditorMode>("edit")

// The chat beside the editor sends `message` as if the person typed it. False when no chat is open.
export const sendToChat = (message: string): boolean => chatSender.value?.(message) ?? false
export const chatSender = shallowRef<((message: string) => boolean) | null>(null)
