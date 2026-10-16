import { useStorage } from "@vueuse/core"
import { call } from "frappe-ui"
import { ref } from "vue"

import { type Artifact, artifactKinds } from "../artifacts"
import { onUserEvent } from "../realtime"

// The home is where a person does their work: their workspace of widgets, the artifacts they open,
// and the assistant beside them. Studio is where things are built.
export type HomeArtifact = Artifact & { modified: string }

export interface View extends HomeArtifact {
	// where the artifact is used, or null while it is not published
	view: string | null
	can_write: boolean
	pinned: boolean
}

export interface Home {
	pinned: HomeArtifact[]
	can_build: boolean
}

export const home = ref<Home | null>(null)
export async function loadHome() {
	home.value = await call<Home>("frappe.ai.home.get_home")
}

export interface Action {
	label: string
	kind: "set" | "workflow" | "create"
}

export interface Widget {
	id: string
	type: "queue" | "inbox" | "chart" | "quick_entry" | "embed" | "note"
	title: string | null
	size: "s" | "m" | "l" | "xl"
	doctype?: string
	name?: string
	chart?: string
	text?: string
	search?: boolean
	actions?: Action[]
}

export interface Workspace {
	widgets: Widget[]
	// the person arranged their own, rather than getting everyone's
	customized: boolean
	// the setup conversation, once one started
	setup: { needed: boolean; site: boolean; chat: string | null }
	can_set_default: boolean
}

export const workspace = ref<Workspace | null>(null)
// bumped when what the widgets show may have changed, so each loads again
export const refreshed = ref(0)

export async function loadWorkspace() {
	const loaded = await call<Workspace>("frappe.ai.workspace.get_workspace")
	if (JSON.stringify(loaded) !== JSON.stringify(workspace.value)) workspace.value = loaded
}

// a person, or the assistant they asked, rearranged the workspace
onUserEvent("studio_workspace", () => workspace.value && loadWorkspace())

export async function saveWorkspace(widgets: Widget[], forEveryone = false) {
	await call("frappe.ai.workspace.save_workspace", { widgets, for_everyone: forEveryone })
	await loadWorkspace()
}

export async function resetWorkspace() {
	await call("frappe.ai.workspace.reset_workspace")
	await loadWorkspace()
}

export const getWidget = <T>(widget: string, txt?: string) => call<T>("frappe.ai.workspace.get_widget", { widget, txt })

export const getView = (doctype: string, name: string) => call<View>("frappe.ai.home.get_view", { doctype, name })

export async function setPinned(artifact: Pick<Artifact, "doctype" | "name">, pinned: boolean) {
	await call("frappe.desk.like.toggle_like", { doctype: artifact.doctype, name: artifact.name, add: pinned ? "Yes" : "No" })
	await loadHome()
}

export const kindOf = (doctype: string) => artifactKinds.find((kind) => kind.doctypes.includes(doctype))

export const viewRoute = (artifact: Pick<Artifact, "doctype" | "name">) =>
	`/home/${kindOf(artifact.doctype)?.kind}/${encodeURIComponent(artifact.name)}`

// the pane beside the page: the chat, the record a widget opened, or the open view's details
export const pane = useStorage<{ open: boolean; tab: "chat" | "record" | "details" }>("home-pane", { open: false, tab: "chat" })

// the record open in the pane, which the chat talks about too
export const openRecord = ref<{ doctype: string; name: string; title?: string } | null>(null)

export function showRecord(doctype: string, name: string, title?: string) {
	openRecord.value = { doctype, name, title }
	pane.value = { open: true, tab: "record" }
}

// the view on screen, which the chat and the details talk about; the person can leave it out of the chat
export const openView = ref<View | null>(null)
export const viewInChat = ref(true)

// the home's conversation, kept while the person moves between views
export const homeChat = ref<string | null>(null)
// a question the ask bar hands a chat that has not started; one that has takes it through `chatSend`
export const question = ref("")
export const chatSend = ref<((message: string) => boolean) | null>(null)

export const askFocus = ref(0)

export function ask(message: string) {
	pane.value = { open: true, tab: "chat" }
	if (homeChat.value && chatSend.value?.(message)) return
	question.value = message
}

const WIDGET_TITLES: Record<string, string> = {
	inbox: "Inbox",
	quick_entry: "New record",
	note: "Note",
}

export function widgetTitle(widget: Widget) {
	return widget.title || WIDGET_TITLES[widget.type] || widget.doctype || ""
}
