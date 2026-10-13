import { useStorage, useDebounceFn } from "@vueuse/core"
import { call } from "frappe-ui"
import { computed, ref } from "vue"

import { type Chat, getHistory } from "./artifacts"
import { onListUpdate } from "./realtime"
import { isReplaying } from "./replay"

export type ChatStatus = "running" | "waiting" | "unread" | null

export const chats = ref<Chat[]>([])
export const loaded = ref(false)
const runs = ref<Record<string, string>>({})
// the `modified` of each chat when its person last had it open
const seen = useStorage<{ since: string; chats: Record<string, string> }>("studio-seen-chats", { since: "", chats: {} })

async function load() {
	const history = await getHistory(50)
	const open = await call("frappe.client.get_list", {
		doctype: "Flow Run",
		filters: { status: ["in", ["Running", "Paused"]], session: ["in", history.map((chat) => chat.name)] },
		fields: ["session", "status"],
		limit_page_length: 50,
	}).catch(() => [])
	runs.value = Object.fromEntries(open.map((run: { session: string; status: string }) => [run.session, run.status]))
	chats.value = history
	loaded.value = true
	// the first visit has read everything before it, by the server's clock
	if (!seen.value.since) seen.value.since = history[0]?.modified ?? "0"
}

export const refreshChats = useDebounceFn(load, 400)

let watching = false
// the list follows every chat and run the site saves, so a chat in another tab shows its progress
export function watchChats() {
	if (watching) return
	watching = true
	load()
	onListUpdate("Flow Session", refreshChats)
	onListUpdate("Flow Run", refreshChats)
}

export function markSeen(session: string) {
	const chat = chats.value.find((chat) => chat.name === session)
	if (chat) seen.value.chats[session] = chat.modified
}

export function chatStatus(chat: Chat, current: string | null): ChatStatus {
	const run = runs.value[chat.name]
	if (run === "Running" || isReplaying(chat.name)) return "running"
	if (run === "Paused") return "waiting"
	if (chat.name === current) return null
	return chat.modified > (seen.value.chats[chat.name] ?? seen.value.since) ? "unread" : null
}

export const chatTitle = (session: string | null) =>
	computed(() => chats.value.find((chat) => chat.name === session)?.title)
