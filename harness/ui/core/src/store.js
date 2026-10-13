import { reactive, watch } from "vue"

import { FlowAPIError } from "./client.js"
import { applyEvent, approvalToAnswer, initialConversation, normalizeSkillCommand, skillCommand } from "./transcript.js"

export const MAX_ATTACHMENTS = 10

function sameArray(left, right) {
	return left.length === right.length && left.every((value, index) => value === right[index])
}

// A run that ended on its own hands the queue its next turn; a pause, a stop, a failure
// or a denied tool call leaves the queue waiting for the user.
function ranItsCourse(reason) {
	return !!reason && !["paused", "aborted", "error", "denied"].includes(reason)
}

function readJSON(key, fallback, storage = globalThis.localStorage) {
	try {
		return JSON.parse(storage.getItem(key)) ?? fallback
	} catch {
		return fallback
	}
}

// One store per chat.
//
// Host options:
//   storageKey     localStorage prefix, so a host can scope saved state per user
//   presentTool    (name, args, result) => { icon, label, subject, stat, expandable, title,
//                  body, argsComponent, resultComponent }, any subset, describing the host's
//                  tools in rows, approvals and expanded output
//   openArtifact   (artifact) => void, called when an artifact card in the transcript is clicked
//   artifactIcon   (artifact) => icon class of an artifact card
//   artifactLayer  (artifact) => the name an artifact card gives its kind, instead of its label
//   openTurn       () => true while the latest turn stays open after its run ends, as if it still ran
//   placeholder    the composer's placeholder, instead of "Reply…" or "Describe what to build…"
//   skills         false hides the composer's "/" skills menu
//   agents         [{ agent, label }] a new chat may start with, as a switch in the composer;
//                  `agent` null is the default one
//   taskCard       component drawing a task a turn's tool sent to another chat ({ task })
//   context        what the host tells the agent with each message: { snapshot() → context or
//                  null, taken as a message is sent; sent(context), once it is delivered or
//                  queued; pending() → chips waiting above the composer, which make a message
//                  worth sending on their own; attached() → chips the message carries along, not
//                  worth sending alone; remove(key); chips(context) → a bubble's chips }
export function createFlowStore(client, options = {}) {
	options = { storageKey: "flow.ui", maxAttachments: MAX_ATTACHMENTS, presentTool: null, ...options }
	const keys = { prefs: `${options.storageKey}.prefs`, queue: `${options.storageKey}.queue` }
	const prefs = { mode: "auto", ...readJSON(keys.prefs, {}) }

	const state = reactive({
		sessionId: null,
		session: null,
		conversation: initialConversation(),
		queued: [], // messages waiting for the run to end
		skills: [],
		loading: false,
		toast: null,
		quotes: [], // thread selections ("Add to chat") quoted under the next message
		agent: null, // the agent a new chat starts with, null for the default
		transcriptOpen: false,
		prefs,
	})

	let stream = null
	let creating = null // in-flight lazy session creation; a double-send shares it
	let sendCount = 0
	let queueCount = 0
	let lastRunEnd = null
	// Waiting messages by session, in sessionStorage so other tabs don't send them too. Several
	// stores share it, one per open chat, so each writes only its own session's entry.
	const savedQueues = () => readJSON(keys.queue, {}, globalThis.sessionStorage)
	function saveQueue(sid, records) {
		const all = savedQueues()
		if (records.length) all[sid] = records
		else delete all[sid]
		try {
			sessionStorage.setItem(keys.queue, JSON.stringify(all))
		} catch {
			// storage blocked: the queue still lasts until the page goes
		}
	}
	watch(
		() => [state.sessionId, JSON.stringify(state.queued.map(waitingRecord))],
		([sid, json]) => sid && saveQueue(sid, JSON.parse(json)),
	)
	let skillsLoaded = null // session id (or "new") whose skills are in state.skills

	function savePrefs() {
		localStorage.setItem(keys.prefs, JSON.stringify(state.prefs))
	}

	function notify(message, kind = "info") {
		state.toast = { message, kind, at: Date.now() }
	}

	async function guard(work) {
		try {
			return await work()
		} catch (error) {
			notify(error instanceof FlowAPIError ? error.message : String(error?.message ?? error), "error")
			return null
		}
	}

	function closeStream() {
		stream?.close()
		stream = null
	}

	async function openSession(sid, { sending = [], config = null } = {}) {
		closeStream()
		swapQueue(sid)
		state.sessionId = sid
		state.session = config ? { title: config.title ?? null, config } : null
		state.skills = []
		skillsLoaded = null
		state.conversation = initialConversation()
		state.conversation.model = config?.model ?? null
		lastRunEnd = null
		// a message sent before this session existed keeps its bubble while the transcript loads
		state.conversation.sending = sending
		state.loading = true
		const info = await guard(() => client.session(sid))
		if (state.sessionId !== sid) return
		const seed = info && (await guard(() => client.entries(sid)))
		if (state.sessionId !== sid) return
		if (!seed) {
			state.session = null
			state.loading = false
			return
		}
		if (seed.latest_seq > info.latest_seq) info.latest_seq = seed.latest_seq
		state.session = info
		state.conversation.model = info.model
		state.conversation.contextTokens = info.context_tokens ?? 0
		for (const entry of seed.entries) applyEvent(state.conversation, entry)
		const lastEnded = seed.entries.findLast((entry) => entry.type === "run_ended" && !entry.subagent_id)
		lastRunEnd = lastEnded?.reason ?? null
		state.conversation.contextWindow ??= info.context_window ?? null
		state.loading = false
		startStream(sid, seed.latest_seq)
		// a run that ran its course while this chat was closed still hands the next waiting message a turn
		const next = state.queued[0]
		if (next && !state.conversation.running && ranItsCourse(lastRunEnd) && lastEnded.seq > next.afterSeq)
			void sendWaiting(next)
	}

	function startStream(sid, since) {
		const own = (stream = client.stream(sid, since))
		;(async () => {
			try {
				for await (const event of own) {
					if (stream !== own || state.sessionId !== sid) return
					handleEvent(event)
				}
			} catch (error) {
				if (stream === own) notify(error.message, "error")
			} finally {
				if (stream === own && state.sessionId === sid) state.loading = false
			}
		})()
	}

	function handleEvent(event) {
		if (event.type === "title_changed") {
			if (state.session) state.session.title = event.title
			return
		}
		applyEvent(state.conversation, event)
		// an error witnessed live shows in full, in the thread it belongs to
		if (event.type === "run_error" && event.seq > (state.session?.latest_seq ?? 0)) {
			const thread = event.subagent_id ? state.conversation.subagents[event.subagent_id] : state.conversation
			thread.liveErrorSeqs.push(event.seq)
		}
		if (event.subagent_id) return
		if (event.type === "user_message") {
			const blocks = Array.isArray(event.content) ? event.content : []
			const expandedText = Array.isArray(event.content)
				? blocks
						.filter((block) => block.type === "text")
						.map((block) => block.text)
						.join("")
				: event.content
			const text = skillCommand(event) ?? expandedText
			const attachmentIds = blocks.filter((block) => block.type === "attachment").map((block) => block.id)
			const steered = state.conversation.steering.findIndex(
				(item) => item.text === text && sameArray(item.attachmentIds, attachmentIds),
			)
			if (steered !== -1) state.conversation.steering.splice(steered, 1)
		}
		// the server discards steering it never consumed, and no echo will clear it
		if (event.type === "run_ended" && ["aborted", "error"].includes(event.reason)) state.conversation.steering = []
		if (event.type === "run_ended") lastRunEnd = event.reason
		const live = event.seq > (state.session?.latest_seq ?? 0)
		if (event.type === "run_ended" && ranItsCourse(event.reason) && live && state.queued.length)
			void sendWaiting(state.queued[0])
		if ((event.type === "run_started" || event.type === "run_ended") && live && state.session)
			state.session.state =
				event.type === "run_started" ? "running" : event.reason === "paused" ? "paused" : "idle"
	}

	// Reset to a blank chat. No server call: send() creates the session lazily.
	function startNewChat() {
		closeStream()
		swapQueue(null)
		state.sessionId = null
		state.session = null
		state.loading = false
		state.skills = []
		skillsLoaded = null
		state.conversation = initialConversation()
	}

	async function newSession({ sending = [] } = {}) {
		const data = await guard(() =>
			client.createSession({ auto_approve: state.prefs.mode === "auto", agent: state.agent }),
		)
		if (!data) return null
		await openSession(data.session_id, { sending, config: data.config })
		return data.session_id
	}

	// the skills a message can start with /skill:<name>, of the open chat or of a new one
	async function loadSkills() {
		const key = state.sessionId ?? "new"
		if (skillsLoaded === key) return
		skillsLoaded = key
		const catalog = await guard(() => (state.sessionId ? client.skills(state.sessionId) : client.previewSkills()))
		if ((state.sessionId ?? "new") === key && catalog) state.skills = catalog.skills ?? []
		else if (!catalog) skillsLoaded = null
	}

	async function send(text, attachments = []) {
		const message = text.trim()
		if (!message && !attachments.length && !options.context?.pending().length) return false
		if (attachments.length > options.maxAttachments) {
			notify(`A message can carry at most ${options.maxAttachments} attachments.`, "error")
			return false
		}
		if (state.conversation.pendingApproval) {
			notify("Answer the approval before sending another message.", "error")
			return false
		}
		const context = options.context?.snapshot() ?? null
		const sent = await queueOrSend(message, attachments, context)
		if (sent) options.context?.sent(context)
		return sent
	}

	// a running turn holds the next message in the queue until it ends, or until the user steers it in
	async function queueOrSend(message, attachments, context) {
		const busy = () => state.conversation.running || state.conversation.sending.length > 0
		if (!state.sessionId || !busy()) return sendNow(message, attachments, context)
		const sid = state.sessionId
		const afterSeq = state.conversation.latestSeq
		const staged = await stageAttachments(sid, attachments)
		if (!staged) return false
		if (state.sessionId !== sid) {
			saveQueue(sid, [...(savedQueues()[sid] ?? []), { message, attachments: staged.attachments, afterSeq, context }])
			return true
		}
		if (!busy() && !state.queued.length && ranItsCourse(lastRunEnd)) return sendNow(message, staged.attachments, context)
		state.queued.push(queueItem(message, staged.attachments, afterSeq, context))
		return true
	}

	// Opens the next turn with its bubble up before the first round trip.
	async function sendNow(message, attachments, context = null) {
		const pending = { key: `sending:${++sendCount}`, entry: userEntry(message, attachments, context) }
		state.conversation.sending.push(pending)
		const sent = await deliver(message, attachments, pending, null, context)
		if (!sent) unsend(pending)
		return sent
	}

	// steer a waiting message into the running turn, or send it now when no run is going
	async function sendQueued(item) {
		if (!state.queued.includes(item)) return
		if (state.conversation.pendingApproval) {
			notify("Answer the approval before sending another message.", "error")
			return
		}
		if (!state.conversation.running) return sendWaiting(item)
		const sid = state.sessionId
		const at = state.queued.indexOf(item)
		unqueue(item)
		const steered = steeringBubble(item.message, item.attachments, [], item.context)
		state.conversation.steering.push(steered)
		const pending = { key: `sending:${++sendCount}`, entry: steered.entry }
		if (await deliver(item.message, item.attachments, pending, steered, item.context)) return
		unsteer(steered)
		if (state.sessionId === sid) state.queued.splice(at, 0, item)
	}

	async function sendWaiting(item) {
		const sid = state.sessionId
		const at = state.queued.indexOf(item)
		unqueue(item)
		if (!(await sendNow(item.message, item.attachments, item.context)) && state.sessionId === sid) state.queued.splice(at, 0, item)
	}

	function removeQueued(item) {
		if (!state.queued.includes(item)) return
		unqueue(item)
		const ids = item.attachments.map((attachment) => attachment.id)
		if (ids.length) void client.cleanupAttachments(state.sessionId, ids).catch(() => {})
	}

	function queueItem(message, attachments, afterSeq, context = null) {
		const chips = context ? (options.context?.chips(context) ?? []) : []
		return {
			key: `queued:${++queueCount}`,
			message,
			attachments,
			afterSeq,
			context,
			label: message || chips.filter((chip) => chip.badge).map((chip) => chip.label).join(", ") || `${attachments.length} attachment(s)`,
		}
	}

	function steeringBubble(message, attachments, attachmentIds = [], context = null) {
		return {
			key: `steering:${++sendCount}`,
			entry: userEntry(message, attachments, context),
			text: normalizeSkillCommand(message) ?? message,
			attachmentIds,
		}
	}

	function waitingRecord({ message, attachments, afterSeq, context }) {
		return { message, attachments, afterSeq, context }
	}

	function swapQueue(sid) {
		if (state.sessionId) saveQueue(state.sessionId, state.queued.map(waitingRecord))
		state.queued = ((sid && savedQueues()[sid]) || []).map((held) =>
			queueItem(held.message, held.attachments, held.afterSeq, held.context ?? null),
		)
	}

	function unqueue(item) {
		const at = state.queued.indexOf(item)
		if (at >= 0) state.queued.splice(at, 1)
	}

	function unsteer(steered) {
		const at = state.conversation.steering.indexOf(steered)
		if (at >= 0) state.conversation.steering.splice(at, 1)
	}

	function unsend(pending) {
		const at = state.conversation.sending.indexOf(pending)
		if (at >= 0) state.conversation.sending.splice(at, 1)
	}

	function userEntry(message, attachments, context = null) {
		const blocks = attachments.map((item) => ({ type: "attachment", id: item.id ?? item.key, name: item.name, kind: item.kind }))
		if (context) blocks.push({ type: "context", context })
		return { type: "user_message", content: [{ type: "text", text: message }, ...blocks], ts: Date.now() / 1000 }
	}

	// the round trips the bubble hides: the session, the attachments, the run
	async function deliver(message, attachments, pending, steered, context = null) {
		if (!state.sessionId) {
			creating ??= newSession({ sending: state.conversation.sending })
			try {
				if (!(await creating)) return false
			} finally {
				creating = null
			}
		}
		const sid = state.sessionId
		const staged = await stageAttachments(sid, attachments)
		if (!staged) return false
		const attachmentIds = staged.attachments.map((item) => item.id)
		let admitted = false
		try {
			if (steered) steered.attachmentIds = attachmentIds
			const seen = state.conversation.entries.length
			const result = await guard(() => client.run(sid, message, attachmentIds, context))
			if (!result) return false
			admitted = true
			if (state.sessionId !== sid) return true
			// the server decides whether it opened a turn or joined the running one
			if (result.status === "steered") {
				const unechoed = state.conversation.sending.includes(pending)
				unsend(pending)
				if (!steered && unechoed)
					state.conversation.steering.push(steeringBubble(message, staged.attachments, attachmentIds, context))
			} else if (steered) {
				unsteer(steered)
				const echoed = state.conversation.entries.slice(seen).some((entry) => entry.type === "user_message")
				if (!echoed) state.conversation.sending.push(pending)
			}
			return true
		} finally {
			if (!admitted && staged.created.length) await client.cleanupAttachments(sid, staged.created).catch(() => {})
		}
	}

	// { attachments: [{ id, name, kind }], created: ids staged by this call }, or null when an upload failed
	async function stageAttachments(sid, attachments) {
		const uploads = attachments.filter((item) => item.file && !item.id).map((item) => item.file)
		const uploaded = uploads.length ? await guard(() => client.uploadAttachments(sid, uploads)) : null
		if (uploads.length && !uploaded) return null
		const created = uploaded?.attachments ?? []
		return {
			attachments: [...attachments.filter((item) => item.id), ...created].map(({ id, name, kind }) => ({ id, name, kind })),
			created: created.map((item) => item.id),
		}
	}

	// Approval answers: "Approve" | "Deny" | free text. Resume fires once every call in the
	// batch has an answer; a deny settles the batch.
	async function answerApproval(callId, answer) {
		const pending = approvalToAnswer(state.conversation)
		if (!pending) return
		pending.answers[callId] = answer
		if (answer === "Deny") {
			for (const call of pending.calls) if (!(call.id in pending.answers)) pending.answers[call.id] = "Deny"
		}
		if (pending.calls.some((c) => !(c.id in pending.answers))) return
		const result = await guard(() => client.resume(state.sessionId, pending.seq, { ...pending.answers }))
		if (result === null) pending.answers = {}
	}

	async function abort() {
		if (!state.sessionId) return
		state.conversation.steering = []
		await guard(() => client.abort(state.sessionId))
	}

	function addQuote(text) {
		if (!state.quotes.includes(text)) state.quotes.push(text)
	}

	function removeQuote(index) {
		state.quotes.splice(index, 1)
	}

	function clearQuotes(sent = null) {
		state.quotes = sent ? state.quotes.filter((quote) => !sent.includes(quote)) : []
	}

	// Approval mode: remembered for new chats, applied to the open one at its next tool gate.
	async function setMode(mode) {
		state.prefs.mode = mode
		savePrefs()
		if (!state.sessionId) return
		const data = await guard(() => client.patchConfig(state.sessionId, { auto_approve: mode === "auto" }))
		if (!data) return
		if (state.session) state.session.config = data.config
		// a batch already waiting is covered by the new mode
		const pending = approvalToAnswer(state.conversation)
		if (mode === "auto" && pending) {
			for (const call of pending.calls) if (!(call.id in pending.answers)) await answerApproval(call.id, "Approve")
		}
	}

	function setAgent(agent) {
		state.agent = agent
	}

	function setTranscriptOpen(open) {
		state.transcriptOpen = open
	}

	async function renameSession(title) {
		const data = await guard(() => client.patchConfig(state.sessionId, { title }))
		if (data && state.session) state.session.title = data.config.title
	}

	async function deleteSession() {
		const sid = state.sessionId
		if ((await guard(() => client.deleteSession(sid))) === null) return
		saveQueue(sid, [])
		if (state.sessionId === sid) {
			state.queued = []
			startNewChat()
		}
	}

	// Object URL for a stored image attachment, null when it is gone; the caller revokes it.
	async function attachmentPreview(sid, attachmentId) {
		if (typeof client.attachmentBlob !== "function") return null
		try {
			return URL.createObjectURL(await client.attachmentBlob(sid, attachmentId))
		} catch {
			return null
		}
	}

	return {
		state,
		client,
		options,
		prepareAttachment: client.prepareAttachment?.bind(client),
		discardAttachments: client.discardAttachments?.bind(client),
		openSession,
		startNewChat,
		loadSkills,
		send,
		sendQueued,
		removeQueued,
		answerApproval,
		abort,
		addQuote,
		removeQuote,
		clearQuotes,
		setMode,
		setAgent,
		setTranscriptOpen,
		renameSession,
		deleteSession,
		attachmentPreview,
		notify,
		detach: closeStream,
	}
}
