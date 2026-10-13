import { useStorage } from "@vueuse/core"
import { computed, ref } from "vue"

// The artifacts open in the editor panel, kept across reloads. A tab belongs to the chat it last opened with.
export interface Tab {
	doctype: string
	name: string
	title: string
	icon: string
	// where the tab was last, with its chat
	path: string
	chat?: string | null
}

const allTabs = useStorage<Tab[]>("studio-tabs", [])
// the chat on screen, whose tabs the panel shows
export const tabChat = ref<string | null>(null)
export const tabs = computed(() => allTabs.value.filter((tab) => (tab.chat ?? null) === tabChat.value))

export const tabKey = (tab: Pick<Tab, "doctype" | "name">) => `${tab.doctype}/${tab.name}`

export const findTab = (doctype: string, name: string) =>
	allTabs.value.find((tab) => tab.doctype === doctype && tab.name === name)

export function openTab(tab: Tab) {
	const open = findTab(tab.doctype, tab.name)
	if (open) Object.assign(open, { path: tab.path, icon: tab.icon, chat: tab.chat })
	else allTabs.value.push(tab)
}

// the tab that takes the closed one's place, if any
export function closeTab(tab: Tab) {
	const shown = tabs.value
	const index = shown.findIndex((open) => tabKey(open) === tabKey(tab))
	if (index === -1) return null
	allTabs.value.splice(allTabs.value.indexOf(shown[index]), 1)
	return shown[index + 1] ?? shown[index - 1] ?? null
}

// a page's title ends with its site's name, as "Code of conduct · Frappeverse 2027"; tabs and the bar show the page's own
export const ownTitle = (title: string) => title.replace(/ · [^·]+$/, "")
