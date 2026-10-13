import { useStorage } from "@vueuse/core"

// The artifacts open in the editor panel, kept across reloads
export interface Tab {
	doctype: string
	name: string
	title: string
	icon: string
	// where the tab was last, with its chat
	path: string
}

export const tabs = useStorage<Tab[]>("studio-tabs", [])

export const tabKey = (tab: Pick<Tab, "doctype" | "name">) => `${tab.doctype}/${tab.name}`

export const findTab = (doctype: string, name: string) =>
	tabs.value.find((tab) => tab.doctype === doctype && tab.name === name)

export function openTab(tab: Tab) {
	const open = findTab(tab.doctype, tab.name)
	if (open) Object.assign(open, { path: tab.path, icon: tab.icon })
	else tabs.value.push(tab)
}

// the tab that takes the closed one's place, if any
export function closeTab(tab: Tab) {
	const index = tabs.value.findIndex((open) => tabKey(open) === tabKey(tab))
	if (index === -1) return null
	tabs.value.splice(index, 1)
	return tabs.value[index] ?? tabs.value[index - 1] ?? null
}
