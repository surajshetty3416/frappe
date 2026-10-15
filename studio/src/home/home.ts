import { useStorage } from "@vueuse/core"
import { call } from "frappe-ui"
import { ref } from "vue"

import { type Artifact, artifactKinds } from "../artifacts"
import { onUserEvent } from "../realtime"

// The home is where a person who uses what was built finds it and opens it; Studio is where it is built.
export type HomeArtifact = Artifact & { modified: string }

export interface View extends HomeArtifact {
	// where the artifact is used, or null while it is not published
	view: string | null
	can_write: boolean
	pinned: boolean
}

// a part of the home, top to bottom; the server fills in what it shows
export interface Section {
	id: string
	type: "pinned" | "recent" | "browse" | "list" | "views" | "embed"
	title: string | null
	doctype?: string
	name?: string
	items?: { doctype: string; name: string }[]
	artifacts?: HomeArtifact[]
	view?: View | null
}

export interface Home {
	sections: Section[]
	pinned: HomeArtifact[]
	// the person arranged their own, rather than getting everyone's
	customized: boolean
	can_build: boolean
	can_set_default: boolean
}

export const home = ref<Home | null>(null)
export async function loadHome() {
	home.value = await call<Home>("frappe.ai.home.get_home")
}

// a person, or the assistant they asked, rearranged the home
onUserEvent("studio_home", () => home.value && loadHome())

export async function saveLayout(sections: Section[], forEveryone = false) {
	const layout = sections.map(({ artifacts, view, ...section }) => section)
	await call("frappe.ai.home.save_home_layout", { sections: layout, for_everyone: forEveryone })
	await loadHome()
}

export async function resetLayout() {
	await call("frappe.ai.home.reset_home_layout")
	await loadHome()
}

export const getView = (doctype: string, name: string) => call<View>("frappe.ai.home.get_view", { doctype, name })

export async function setPinned(artifact: Pick<Artifact, "doctype" | "name">, pinned: boolean) {
	await call("frappe.desk.like.toggle_like", { doctype: artifact.doctype, name: artifact.name, add: pinned ? "Yes" : "No" })
	await loadHome()
}

export const kindOf = (doctype: string) => artifactKinds.find((kind) => kind.doctypes.includes(doctype))

export const viewRoute = (artifact: Pick<Artifact, "doctype" | "name">) =>
	`/home/${kindOf(artifact.doctype)?.kind}/${encodeURIComponent(artifact.name)}`

// the pane beside the page: the chat, or the open view's details
export const pane = useStorage<{ open: boolean; tab: "chat" | "details" }>("home-pane", { open: false, tab: "chat" })

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

const SECTION_TITLES: Record<string, string> = {
	pinned: "Pinned",
	recent: "Recently updated",
	browse: "Browse",
	views: "Views",
}

export function sectionTitle(section: Section) {
	if (section.title) return section.title
	if (section.type === "list") return kindOf(section.doctype ?? "")?.title ?? section.doctype ?? ""
	if (section.type === "embed") return section.view?.title ?? section.name ?? ""
	return SECTION_TITLES[section.type]
}
