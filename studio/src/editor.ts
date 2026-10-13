import type { Component } from "vue"

// What a layer implements to open its artifact in the shell. The shell draws the tabs, the
// artifact bar, the drawers and the selection; the layer renders the preview and answers
// questions about it. Methods are read inside computeds, so reactive state they read updates the shell.
export interface ArtifactEditor {
	// the real output of the artifact the route names, filling the panel and nothing else
	preview: Component
	title(): string
	rename(title: string): Promise<unknown>
	status(): ArtifactStatus
	primaryAction(): ArtifactAction | null
	details(): ArtifactDetail[]
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
	// at most four, shown on the selection's toolbar
	properties(id: string): ElementProperty[]
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
	type: "color" | "select"
	value: string
	options?: { label: string; value: string }[]
	set(value: string): void
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
