<template>
	<div class="flex-none px-4 pb-4">
		<div class="relative mx-auto max-w-[760px]">
			<!-- the skills a "/" offers -->
			<PalettePanel v-if="menuOpen" title="Skills" :autofocus="false" @close="closeMenu">
				<div class="overflow-y-auto p-1">
					<button
						v-for="skill in matches"
						:key="skill.name"
						type="button"
						data-palette-item
						class="flex w-full items-center gap-2 rounded-4 px-2 py-1.5 text-left"
						@click="pickSkill(skill)"
					>
						<span class="lucide-book-open size-4 flex-none text-ink-gray-5" />
						<span class="flex-none text-base text-ink-gray-8">{{ skill.name }}</span>
						<span class="min-w-0 flex-1 truncate text-sm text-ink-gray-5">{{ skill.description }}</span>
					</button>
					<p v-if="!matches.length" class="px-2 py-4 text-center text-sm text-ink-gray-5">No matching skills</p>
				</div>
			</PalettePanel>

			<!-- messages waiting for the run to end, and what waits to join the next message -->
			<div v-if="flow.state.queued.length" class="mb-2 flex flex-col items-start gap-1.5">
				<span
					v-for="item in flow.state.queued"
					:key="item.key"
					class="flex h-7 max-w-full items-center gap-1 rounded-4 border border-outline-gray-2 bg-surface-base pl-2 pr-1"
				>
					<span class="lucide-clock size-3.5 flex-none text-ink-gray-5" />
					<span class="min-w-0 truncate text-sm text-ink-gray-7">{{ item.label }}</span>
					<button
						type="button"
						class="grid size-5 flex-none place-items-center rounded-3 text-ink-gray-5 hover:bg-surface-gray-2 hover:text-ink-gray-8"
						:title="running ? 'Add it to the running turn' : 'Send it now'"
						@click="steerQueued(item)"
					>
						<span class="lucide-corner-down-left size-3.5" />
					</button>
					<button
						type="button"
						class="grid size-5 flex-none place-items-center rounded-3 text-ink-gray-5 hover:bg-surface-gray-2 hover:text-ink-gray-8"
						title="Remove from queue"
						@click="dropQueued(item)"
					>
						<span class="lucide-x size-3.5" />
					</button>
				</span>
			</div>
			<div v-if="contextChips.length" class="mb-2 flex flex-wrap gap-1.5">
				<template v-for="chip in contextChips" :key="chip.key">
					<!-- an offered chip is not sent until picked -->
					<Button
						v-if="chip.suggested"
						data-context-chip-suggested
						variant="ghost"
						icon-left="lucide-plus"
						class="max-w-full !text-ink-gray-5"
						:label="chip.label"
						:tooltip="`Add ${chip.label} to the message`"
						@click="flow.options.context.pick(chip.key)"
					/>
					<span v-else data-context-chip :class="[chipClass, '!max-w-full']" :title="chip.title">
						<ContextChipIcon :chip="chip" />
						<span class="min-w-0 truncate text-sm text-ink-gray-8">{{ chip.label }}</span>
						<button type="button" :class="chipRemoveClass" title="Remove" @click="flow.options.context.remove(chip.key)">
							<span class="lucide-x size-3" />
						</button>
					</span>
				</template>
			</div>

			<div
				ref="grid"
				class="grid grid-cols-[auto_minmax(0,1fr)_auto] items-end gap-x-1 gap-y-2 rounded-6 border border-outline-gray-2 bg-surface-base p-2 shadow-sm focus-within:border-outline-gray-3"
			>
				<!-- one row while the message fits a line beside the controls; the text takes its own row once it grows -->
				<div v-if="imageTiles.length" class="col-span-3 flex flex-wrap gap-1.5 px-1 pt-1">
					<figure
						v-for="{ item, i } in imageTiles"
						:key="item.key"
						class="group/attachment relative size-16 flex-none overflow-hidden rounded-4 border border-outline-gray-2"
						:title="item.name"
					>
						<button type="button" class="block size-full cursor-zoom-in" @click="viewer = item">
							<img :src="item.previewUrl" :alt="item.name" class="size-full object-cover" />
						</button>
						<button
							type="button"
							class="absolute right-1 top-1 grid size-5 place-items-center rounded-full border border-outline-gray-2 bg-surface-base text-ink-gray-6 opacity-0 hover:text-ink-gray-9 group-hover/attachment:opacity-100"
							title="Remove attachment"
							:disabled="submitting"
							@click="removeAttachment(i)"
						>
							<span class="lucide-x size-3" />
						</button>
						<span v-if="item.preparing" class="absolute bottom-1 left-1 grid size-5 place-items-center rounded-3 bg-surface-base" role="status">
							<span class="lucide-loader-circle size-3.5 animate-spin" />
						</span>
					</figure>
				</div>
				<div v-if="quotes.length || fileChips.length" class="col-span-3 flex flex-wrap items-center gap-1.5 px-1 pt-1">
					<span v-for="(quote, i) in quotes" :key="`quote:${i}`" :class="chipClass" :title="quote">
						<span class="lucide-quote size-4 flex-none text-ink-gray-5" />
						<span class="min-w-0 truncate text-sm text-ink-gray-8">{{ quoteLabel(quote) }}</span>
						<button type="button" :class="chipRemoveClass" title="Remove quote" :disabled="submitting" @click="flow.removeQuote(i)">
							<span class="lucide-x size-3" />
						</button>
					</span>
					<span v-for="{ item, i } in fileChips" :key="item.key" :class="chipClass" :title="item.name">
						<span
							:class="item.preparing ? 'lucide-loader-circle animate-spin' : 'lucide-file-text'"
							class="size-4 flex-none text-ink-gray-5"
						/>
						<span class="min-w-0 flex-1 truncate text-sm text-ink-gray-8">{{ item.name }}</span>
						<button type="button" :class="chipRemoveClass" title="Remove attachment" :disabled="submitting" @click="removeAttachment(i)">
							<span class="lucide-x size-3" />
						</button>
					</span>
				</div>
				<p v-for="item in attachments.filter((item) => item.error)" :key="item.key" class="col-span-3 px-1 text-sm text-ink-red-6">
					Could not prepare {{ item.name }}: {{ item.error }}
					<button type="button" class="underline" :disabled="submitting" @click="prepareAttachment(item)">Retry</button>
				</p>
				<Button
					v-if="attachable"
					variant="ghost"
					icon="lucide-plus"
					tooltip="Attach files"
					:class="compact ? '' : 'order-2'"
					:disabled="submitting"
					@click="fileInput?.click()"
				/>
				<div class="relative self-center" :class="compact ? 'col-start-2' : 'order-1 col-span-3'">
					<!-- known skill commands show in blue under the transparent text -->
					<div
						v-if="skillParts"
						aria-hidden="true"
						class="pointer-events-none absolute inset-0 overflow-hidden whitespace-pre-wrap break-words px-1.5 py-1 text-base leading-5"
					>
						<div :style="{ transform: `translateY(-${textScrollTop}px)` }">
							<span v-for="(part, i) in skillParts" :key="i" :class="part.skill ? 'text-ink-blue-6' : 'text-ink-gray-8'">{{ part.text }}</span>
						</div>
					</div>
					<textarea
						ref="box"
						v-model="text"
						rows="1"
						:disabled="submitting"
						:placeholder="placeholder"
						style="caret-color: var(--ink-gray-9)"
						class="relative block max-h-44 min-h-7 w-full resize-none border-0 bg-transparent px-1.5 py-1 text-base leading-5 outline-none placeholder:text-ink-gray-4 focus:ring-0"
						:class="skillParts ? 'text-transparent' : 'text-ink-gray-8'"
						@keydown="onKey"
						@paste="onPaste"
						@scroll="textScrollTop = $event.currentTarget.scrollTop"
						@input="syncCaret"
						@keyup="syncCaret"
						@click="syncCaret"
					/>
				</div>
				<input ref="fileInput" type="file" multiple class="hidden" @change="onFilesPicked" />
				<div ref="controls" class="col-start-3 flex items-center gap-1" :class="compact ? '' : 'order-3'">
					<!-- a new chat picks its agent: build here, or send each task to its own chat -->
					<TabButtons
						v-if="agentOptions"
						aria-label="Agent"
						variant="ghost"
						class="mr-1"
						:options="agentOptions"
						:model-value="flow.state.agent ?? ''"
						@update:model-value="(value) => flow.setAgent(value || null)"
					/>
					<Dropdown v-if="flow.options.approvals !== false" :options="modeOptions" align="end">
						<Button variant="ghost" :label="modeLabel" icon-right="lucide-chevron-down" />
					</Dropdown>
					<Button
						v-if="running && !submitting"
						variant="solid"
						icon="lucide-square"
						class="!rounded-full"
						tooltip="Stop"
						@click="flow.abort()"
					/>
					<Button
						v-else
						variant="solid"
						icon="lucide-arrow-up"
						class="!rounded-full"
						tooltip="Send"
						:disabled="!canSend"
						:loading="submitting"
						@click="submit"
					/>
				</div>
			</div>
			<ImageViewer v-if="viewer" :src="viewer.previewUrl" :alt="viewer.name" @close="viewer = null" />
		</div>
	</div>
</template>

<script setup>
import { computed, inject, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue"
import { Button, Dropdown, TabButtons } from "frappe-ui"

import { quoteBlock, skillSegments } from "../transcript.js"
import ContextChipIcon from "./ContextChipIcon.vue"
import ImageViewer from "./ImageViewer.vue"
import PalettePanel from "./PalettePanel.vue"

const flow = inject("flow")

const text = ref("")
const box = ref(null)
const fileInput = ref(null)
const attachments = ref([])
const viewer = ref(null)
const submitting = ref(false)
const textScrollTop = ref(0)
const caretPos = ref(0)
let attachmentKey = 0
const preparations = new Map()
let preparationQueue = Promise.resolve()

const IMAGE_TYPES = new Set(["image/png", "image/jpeg", "image/gif", "image/webp", "image/bmp"])

const running = computed(() => flow.state.conversation.running)
// once the text wraps it keeps its own row until the box empties, or it would flip back and forth
const wrapped = ref(false)
// a narrow box, like a new chat's beside an open artifact, leaves the text no room beside the controls
const MIN_TEXT_WIDTH = 240
const roomy = ref(true)
const compact = computed(() => roomy.value && !wrapped.value && !text.value.includes("\n"))
const agentOptions = computed(() =>
	!flow.state.sessionId && flow.options.agents?.length > 1
		? flow.options.agents.map(({ agent, label }) => ({ value: agent ?? "", label }))
		: null,
)
// the agent of the open chat, or the one a new chat starts with
const agentEntry = computed(() => {
	const agent = flow.state.sessionId ? flow.state.session?.config?.agent : flow.state.agent
	return flow.options.agents?.find((entry) => (entry.agent ?? null) === (agent ?? null))
})
const attachable = computed(() => flow.options.attachments !== false)
const skillsOn = computed(() => flow.options.skills !== false && agentEntry.value?.skills !== false)
const placeholder = computed(
	() =>
		(!flow.state.sessionId && agentEntry.value?.placeholder) ||
		(flow.options.placeholder ??
			(flow.state.sessionId ? "Reply…" : "Describe what to build…")),
)

const MODES = { auto: "Auto-approve", ask: "Ask first" }
const currentMode = computed(() => {
	if (!flow.state.sessionId) return flow.state.prefs.mode
	const flag = flow.state.session?.config?.auto_approve
	return flag == null ? flow.state.prefs.mode : flag ? "auto" : "ask"
})
const modeLabel = computed(() => MODES[currentMode.value])
const modeOptions = computed(() =>
	Object.entries(MODES).map(([mode, label]) => ({
		label,
		icon: currentMode.value === mode ? "lucide-check" : undefined,
		onClick: () => flow.setMode(mode),
	})),
)

function addFiles(files) {
	for (const file of files) {
		if (attachments.value.length >= flow.options.maxAttachments) {
			flow.notify(`A message can carry at most ${flow.options.maxAttachments} attachments.`, "error")
			return
		}
		if (attachments.value.some((item) => item.file?.name === file.name && item.file?.size === file.size)) continue
		const image = IMAGE_TYPES.has(file.type.toLowerCase())
		attachments.value.push({
			key: `local:${attachmentKey++}`,
			name: file.name,
			kind: image ? "image" : "file",
			file,
			previewUrl: image ? URL.createObjectURL(file) : null,
		})
		if (flow.prepareAttachment) void prepareAttachment(attachments.value.at(-1))
	}
}

function discardAttachment(item) {
	if (item.id && item.file && flow.discardAttachments) void flow.discardAttachments([item.id]).catch(() => {})
}

// one at a time: a batch of large files would otherwise extract all at once
function prepareAttachment(item) {
	if (preparations.has(item.key)) return preparations.get(item.key)
	item.preparing = true
	item.error = null
	const pending = preparationQueue.then(async () => {
		try {
			if (!attachments.value.includes(item)) return
			Object.assign(item, await flow.prepareAttachment(item.file, flow.state.conversation.model))
			if (!attachments.value.includes(item)) discardAttachment(item)
		} catch (error) {
			item.error = error.message || "Please try again."
		} finally {
			item.preparing = false
			preparations.delete(item.key)
		}
	})
	preparationQueue = pending
	preparations.set(item.key, pending)
	return pending
}

function clearAttachments(discard = true) {
	viewer.value = null
	for (const item of attachments.value) {
		if (item.previewUrl) URL.revokeObjectURL(item.previewUrl)
		if (discard) discardAttachment(item)
	}
	attachments.value = []
}

function onFilesPicked(event) {
	addFiles([...event.target.files])
	event.target.value = ""
	nextTick(() => box.value?.focus())
}

function onPaste(event) {
	if (!attachable.value) return
	const images = [...(event.clipboardData?.items ?? [])]
		.filter((item) => item.kind === "file" && item.type.startsWith("image/"))
		.map((item) => item.getAsFile())
		.filter(Boolean)
	if (!images.length) return
	event.preventDefault()
	addFiles(images)
}

function removeAttachment(index) {
	const [removed] = attachments.value.splice(index, 1)
	if (removed.previewUrl) URL.revokeObjectURL(removed.previewUrl)
	discardAttachment(removed)
	nextTick(() => box.value?.focus())
}

// selectionStart is not reactive: resync it so the "/" menu sees caret moves
function syncCaret() {
	caretPos.value = box.value?.selectionStart ?? text.value.length
}

// the "/word" being typed at the caret, when it starts a word
const slash = computed(() => {
	if (!skillsOn.value) return null
	const head = text.value.slice(0, caretPos.value)
	const at = head.lastIndexOf("/")
	if (at === -1) return null
	const query = head.slice(at + 1)
	if (/\s/.test(query) || (at > 0 && !/\s/.test(head[at - 1]))) return null
	return { start: at, query }
})
const slashDismissed = ref(false)
watch(
	() => slash.value?.start,
	(start) => {
		if (start !== undefined) slashDismissed.value = false
	},
)
watch(slash, (value) => value && void flow.loadSkills())
const matches = computed(() => {
	const q = (slash.value?.query ?? "").replace(/^skill:/, "").toLowerCase()
	return (flow.state.skills ?? []).filter((skill) => skill.name.toLowerCase().startsWith(q))
})
const menuOpen = computed(() => !!slash.value && !slashDismissed.value)

function closeMenu() {
	slashDismissed.value = true
	nextTick(() => box.value?.focus())
}

function pickSkill(skill) {
	const { start, query } = slash.value
	const end = start + 1 + query.length
	const head = `${text.value.slice(0, start)}/skill:${skill.name} `
	text.value = head + text.value.slice(end).replace(/^ /, "")
	caretPos.value = head.length
	slashDismissed.value = true
	nextTick(() => {
		box.value?.focus()
		box.value?.setSelectionRange(head.length, head.length)
	})
}

const skillParts = computed(() => {
	const parts = skillSegments(text.value, (flow.state.skills ?? []).map((skill) => skill.name))
	return parts.some((part) => part.skill) ? parts : null
})

// grow with content up to the CSS max-height, then scroll
function autosize() {
	const el = box.value
	if (!el) return
	el.style.height = "auto"
	el.style.height = `${el.scrollHeight}px`
	if (!text.value) wrapped.value = false
	// a second line of text: 20px lines and 8px of padding
	else if (el.scrollHeight > 36) wrapped.value = true
	textScrollTop.value = el.scrollTop
}
watch(text, () => nextTick(autosize))

// the box's width changes as the panel beside the chat opens or is dragged
let resizes = null
onMounted(() => {
	let width = 0
	resizes = new ResizeObserver(([entry]) => {
		if (entry.contentRect.width === width) return
		width = entry.contentRect.width
		autosize()
	})
	if (box.value) resizes.observe(box.value)
})
onBeforeUnmount(() => resizes?.disconnect())

// neither width depends on the layout `roomy` picks, so it cannot flip back and forth
const grid = ref(null)
const controls = ref(null)
let rooms = null
onMounted(() => {
	rooms = new ResizeObserver(() => {
		if (grid.value && controls.value) roomy.value = grid.value.clientWidth - controls.value.offsetWidth >= MIN_TEXT_WIDTH
	})
	;[grid.value, controls.value].forEach((el) => el && rooms.observe(el))
})
onBeforeUnmount(() => rooms?.disconnect())

onMounted(() => {
	autosize()
	box.value?.focus()
	window.addEventListener("keydown", onWindowKey)
})
onBeforeUnmount(() => {
	window.removeEventListener("keydown", onWindowKey)
	clearAttachments(!submitting.value)
})
watch(
	() => flow.state.sessionId,
	() => {
		if (!submitting.value) {
			clearAttachments()
			flow.clearQuotes()
		}
		nextTick(() => box.value?.focus())
	},
)

const quotes = computed(() => flow.state.quotes)
const quoteLabel = (quote) => quote.replace(/\s+/g, " ").slice(0, 120)
watch(
	() => quotes.value.length,
	(count, prev) => {
		if (count > (prev ?? 0)) nextTick(() => box.value?.focus())
	},
)
const isImageTile = (item) => item.kind === "image" && !!item.previewUrl
const staged = (keep) =>
	attachments.value.map((item, i) => ({ item, i })).filter(({ item }) => keep(item))
const imageTiles = computed(() => staged(isImageTile))
const fileChips = computed(() => staged((item) => !isImageTile(item)))
const chipClass = "flex h-7 max-w-[240px] items-center gap-1.5 rounded-4 border border-outline-gray-2 bg-surface-base pl-2 pr-1"
const chipRemoveClass = "grid size-5 flex-none place-items-center rounded-3 text-ink-gray-5 hover:bg-surface-gray-2 hover:text-ink-gray-8"
// what rides along with the message (the open artifact), then what makes one worth sending on its own (comments)
const pendingChips = computed(() => flow.options.context?.pending() ?? [])
const contextChips = computed(() => [...(flow.options.context?.attached?.() ?? []), ...pendingChips.value])
const canSend = computed(
	() =>
		!submitting.value &&
		(text.value.trim().length > 0 || attachments.value.length > 0 || quotes.value.length > 0 || pendingChips.value.length > 0),
)

function onKey(e) {
	if (e.key === "Enter" && !e.shiftKey && !(menuOpen.value && matches.value.length)) {
		e.preventDefault()
		submit()
	}
	if (e.key === "Escape") {
		// close the menu first; a bare Escape stops the running turn
		e.stopPropagation()
		if (menuOpen.value) closeMenu()
		else if (running.value && !e.repeat) flow.abort()
	}
}

// Escape stops the turn even when focus is outside the box. An open dialog, menu or list
// owns it, though closing one leaves the event unprevented, and so does whatever else on
// the page took it, once every listener has run.
const LAYERS = '[role="dialog"], [role="menu"], [role="listbox"]'
function onWindowKey(e) {
	if (e.key !== "Escape" || e.repeat || menuOpen.value || document.querySelector(LAYERS)) return
	setTimeout(() => {
		if (!e.defaultPrevented && running.value) flow.abort()
	})
}

async function submit() {
	if (submitting.value) return
	const draftText = text.value
	const value = draftText.trim()
	if (!canSend.value) return
	// quotes travel as blockquotes under the message
	const selectedQuotes = [...quotes.value]
	const outgoing = [value, selectedQuotes.map(quoteBlock).join("\n\n")].filter(Boolean).join("\n\n")
	const selectedAttachments = [...attachments.value]
	const sendingSessionId = flow.state.sessionId
	submitting.value = true
	try {
		const pending = selectedAttachments.map((item) => preparations.get(item.key)).filter(Boolean)
		if (pending.length) await Promise.all(pending)
		if (flow.state.sessionId !== sendingSessionId) return
		if (selectedAttachments.some((item) => item.error || !attachments.value.includes(item))) return
		// the box empties as the bubble appears; a send that never lands hands the text back
		text.value = ""
		if (await flow.send(outgoing, selectedAttachments)) {
			clearAttachments(false)
			flow.clearQuotes(selectedQuotes)
		} else {
			text.value = draftText
		}
	} finally {
		submitting.value = false
		nextTick(() => box.value?.focus())
	}
}

function steerQueued(item) {
	flow.sendQueued(item)
	box.value?.focus()
}

function dropQueued(item) {
	flow.removeQueued(item)
	box.value?.focus()
}

function prefill(value) {
	text.value = value
	caretPos.value = value.length
	nextTick(() => box.value?.focus())
}

defineExpose({ prefill })
</script>
