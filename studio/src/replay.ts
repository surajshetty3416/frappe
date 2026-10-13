import { useStorage } from "@vueuse/core"
import { call } from "frappe-ui"
import { reactive, watch } from "vue"

export interface Recording {
	name: string
	title: string
	position: number
	steps: number
}

export interface Replay {
	session: string
	recording: string
	title: string
	step: number
	steps: number
	status: "Ready" | "Playing" | "Done" | "Failed"
	error: string | null
	live: boolean
}

// the part of a chat's store a replay reads: its stream, and what its person sent
export interface ChatState {
	conversation: { latestSeq: number; running: boolean; sending: unknown[] }
	queued: unknown[]
}

// by session; null for a chat that is not a replay
export const replays = reactive(new Map<string, Replay | null>())
const playing = reactive(new Set<string>())
const stepping = reactive(new Set<string>())

// how many times faster than recorded a replay plays
export const speeds = [1, 2, 4, 8]
export const speed = useStorage("studio-replay-speed", 4)

export const isPlaying = (session: string) => playing.has(session)
export const isStepping = (session: string) => stepping.has(session)
export const isReplaying = (session: string) => playing.has(session) || stepping.has(session)

export const listRecordings = () => call<Recording[]>("frappe.ai.replay.list_recordings")

export async function startReplay(recording: string) {
	const replay = await call<Replay>("frappe.ai.replay.start_replay", { recording })
	replays.set(replay.session, replay)
	return replay
}

export async function loadReplay(session: string) {
	const replay = await call<Replay | null>("frappe.ai.replay.get_replay", { session }).catch(() => null)
	replays.set(session, replay)
	return replay
}

export async function nextRecording(recording: string) {
	const recordings = await listRecordings()
	return recordings[recordings.findIndex((item) => item.name === recording) + 1] ?? null
}

const spoke = (chat: ChatState) => chat.queued.length > 0 || chat.conversation.sending.length > 0

// play the next step, and answer once its run ended; false when it could not start
export async function stepReplay(session: string, chat: ChatState) {
	if (stepping.has(session)) return false
	stepping.add(session)
	try {
		replays.set(session, await call<Replay>("frappe.ai.replay.play_step", { session, speed: speed.value }))
		await runEnded(session, chat)
		return true
	} catch {
		await loadReplay(session)
		return false
	} finally {
		stepping.delete(session)
	}
}

// step until the end, a failure, a pause or a message of the person's own
export async function playReplay(session: string, chat: ChatState) {
	playing.add(session)
	try {
		while (playing.has(session) && !spoke(chat)) {
			const replay = replays.get(session)
			if (replay?.status !== "Ready" || replay.live || replay.error) break
			if (!(await stepReplay(session, chat))) break
		}
	} finally {
		playing.delete(session)
	}
}

// the step playing finishes first
export const pauseReplay = (session: string) => playing.delete(session)

// The site settles a step once its run ended. The stream says when that may be: an event
// that leaves the chat not running, which a step's first event can be too, so the site has
// the last word, and is asked again every 2s should the stream miss the end.
async function runEnded(session: string, chat: ChatState) {
	for (;;) {
		const seq = chat.conversation.latestSeq
		await new Promise<void>((resolve) => {
			const stop = watch(
				() => chat.conversation.latestSeq > seq && !chat.conversation.running,
				(ended) => ended && done(),
			)
			const timer = window.setTimeout(done, 2000)
			function done() {
				stop()
				clearTimeout(timer)
				resolve()
			}
		})
		if ((await loadReplay(session))?.status !== "Playing") return
	}
}
