import { useDebounceFn } from "@vueuse/core"
import { call } from "frappe-ui"
import { computed, ref } from "vue"

import { type Chat, getHistory } from "./artifacts"
import { onListUpdate } from "./realtime"

// as many as the server lists, so each project's section in the sidebar can show all of its own
const CHAT_LIMIT = 100

export const chats = ref<Chat[]>([])
// a recording's earlier replays, which its latest one replaces in the list
export const superseded = ref(new Set<string>())

export async function loadChats() {
	const history = await getHistory(CHAT_LIMIT)
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
}

export const refreshChats = useDebounceFn(loadChats, 400)

let watching = false
// the list follows every chat the site saves, so a chat made in another tab shows up
export function watchChats() {
	if (watching) return
	watching = true
	loadChats()
	onListUpdate("Flow Session", refreshChats)
}

export const chatTitle = (session: string | null) =>
	computed(() => chats.value.find((chat) => chat.name === session)?.title)
