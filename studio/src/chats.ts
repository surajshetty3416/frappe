import { useStorage, useDebounceFn } from "@vueuse/core"
import { call } from "frappe-ui"
import { computed, ref } from "vue"

import { type Chat, getHistory } from "./artifacts"
import { onListUpdate } from "./realtime"
import { isReplaying, replays } from "./replay"

export type ChatStatus = "running" | "waiting" | "unread" | null

// as many as the server lists, so each project's section in the sidebar can show all of its own
const CHAT_LIMIT = 100

export const chats = ref<Chat[]>([])
// a recording's earlier replays, which its latest one replaces in the list
export const superseded = ref(new Set<string>())
const runs = ref<Record<string, string>>({})
// the `modified` of each chat when its person last had it open
const seen = useStorage<{ since: string; chats: Record<string, string> }>("studio-seen-chats", { since: "", chats: {} })

export async function loadChats() {
	const history = await getHistory(CHAT_LIMIT)
	const open = await call("frappe.client.get_list", {
		doctype: "Flow Run",
		filters: { status: ["in", ["Running", "Paused"]], session: ["in", history.map((chat) => chat.name)] },
		fields: ["session", "status"],
		limit_page_length: CHAT_LIMIT,
	}).catch(() => [])
	runs.value = Object.fromEntries(open.map((run: { session: string; status: string }) => [run.session, run.status]))
	const replayed = await call<{ session: string; recording: string }[]>("frappe.client.get_list", {
		doctype: "Flow Replay",
		filters: { session: ["in", history.map((chat) => chat.name)] },
		fields: ["session", "recording"],
		limit_page_length: CHAT_LIMIT,
	}).catch(() => [])
	const recordingOf = new Map(replayed.map((replay) => [replay.session, replay.recording]))
	// the history is newest first, so the first replay of a recording is its latest
	const latest = new Set<string>()
	superseded.value = new Set(
		history.filter((chat) => {
			const recording = recordingOf.get(chat.name)
			if (!recording || latest.has(recording)) return Boolean(recording)
			latest.add(recording)
			return false
		}).map((chat) => chat.name)
	)
	chats.value = history
	// the first visit has read everything before it, by the server's clock
	if (!seen.value.since) seen.value.since = history.reduce((latest, chat) => (chat.modified > latest ? chat.modified : latest), "0")
}

export const refreshChats = useDebounceFn(loadChats, 400)

let watching = false
// the list follows every chat and run the site saves, so a chat in another tab shows its progress
export function watchChats() {
	if (watching) return
	watching = true
	loadChats()
	onListUpdate("Flow Session", refreshChats)
	onListUpdate("Flow Run", refreshChats)
}

export function markSeen(session: string) {
	const chat = chats.value.find((chat) => chat.name === session)
	if (chat) seen.value.chats[session] = chat.modified
}

export function chatStatus(chat: Chat, current: string | null): ChatStatus {
	// a replay says itself when its step ended; the list may hear of it later
	const replay = replays.get(chat.name)
	const run = replay && !replay.live ? replay.status === "Playing" && "Running" : runs.value[chat.name]
	if (run === "Running" || isReplaying(chat.name)) return "running"
	if (run === "Paused") return "waiting"
	if (chat.name === current) return null
	return chat.modified > (seen.value.chats[chat.name] ?? seen.value.since) ? "unread" : null
}

export const chatTitle = (session: string | null) =>
	computed(() => chats.value.find((chat) => chat.name === session)?.title)
