<template>
	<div class="relative min-h-0 flex-1">
		<div ref="scroller" class="h-full overflow-y-auto px-4" @scroll="onScroll" @mousedown="onMouseDown">
			<LoadingState v-if="loading" class="h-full justify-center text-sm text-ink-gray-5" />
			<div v-else-if="!blank" ref="thread" class="flow-thread mx-auto flex max-w-[760px] flex-col gap-3 pb-16 pt-12">
				<template v-for="(item, i) in items" :key="item.key">
					<!-- 12px between the rows of a turn, 24px between turns -->
					<UserBubble v-if="item.kind === 'user'" :class="i ? 'mt-3' : ''" :entry="item.entry" />
					<TurnFold
						v-else-if="item.kind === 'turn-fold'"
						:data-turn-fold="item.turnKey"
						:label="item.label"
						:expanded="item.expanded"
						@toggle="toggleTurn(item)"
					/>
					<AssistantText v-else-if="item.kind === 'text'" :block="item.block" />
					<ThoughtStep
						v-else-if="item.kind === 'thinking'"
						:id="item.key"
						:class="tightGap(i)"
						:block="item.block"
						:live="item.live"
					/>
					<ToolGroup
						v-else-if="item.kind === 'group'"
						:class="tightGap(i)"
						:steps="item.steps"
						:sealed="i < turnEnd - 1 || !conversation.running"
					/>
					<div v-else-if="item.kind === 'turn-tasks' && flow.options.taskCard" class="flow-turn-tasks flex flex-col gap-2">
						<component :is="flow.options.taskCard" v-for="task in item.tasks" :key="task.key" :task="task" />
					</div>
					<div v-else-if="item.kind === 'turn-artifacts'" class="flow-turn-artifacts flex flex-col gap-2">
						<!-- more than three cards fold into one row that opens to them -->
						<ArtifactGroup v-if="item.artifacts.length > 3" :artifacts="item.artifacts" />
						<template v-else>
							<ArtifactCard v-for="artifact in item.artifacts" :key="artifact.route" :artifact="artifact" />
						</template>
					</div>
					<!-- a turn's copy action reveals on hover -->
					<div v-else-if="item.kind === 'turn-copy'" class="flow-turn-copy -mt-1 flex items-center gap-1">
						<CopyButton :text="item.text" title="Copy response" />
					</div>
					<div v-else-if="item.kind === 'compaction'" class="flex items-center gap-2 text-sm text-ink-gray-5">
						<span class="lucide-archive size-4 flex-none" />
						<span>Context compacted</span>
					</div>
					<p v-else-if="item.kind === 'notice'" class="text-sm text-ink-gray-5">{{ item.text }}</p>
					<div v-else-if="item.kind === 'system'" class="flex items-center gap-2 text-sm text-ink-gray-5">
						<span class="lucide-circle-check size-4 flex-none" />
						<span>{{ item.text }}</span>
					</div>
					<div
						v-else-if="item.kind === 'error'"
						class="break-words rounded-4 border border-outline-red-1 bg-surface-red-1 px-3 py-2 text-sm text-ink-red-6"
					>
						{{ item.error.message }}
					</div>
				</template>

				<!-- a batch answers one call at a time, so the next call takes the card over -->
				<ApprovalCard
					v-if="approval"
					:key="approval.call.id"
					:call="approval.call"
					:position="approval.position"
					:total="approval.total"
				/>

				<!-- the turn at work: what it is doing and for how long -->
				<div v-else-if="working" class="flex items-center gap-2 text-sm">
					<span class="lucide-loader-circle size-4 flex-none animate-spin text-ink-gray-5" />
					<span class="flow-shimmer">{{ liveLabel }}</span>
					<span v-if="elapsed" class="tabular-nums text-ink-gray-5">{{ elapsed }}</span>
				</div>

				<!-- what the host adds at the thread's end -->
				<div ref="end" class="empty:hidden"><slot name="end" /></div>
			</div>
		</div>

		<!-- text scrolled toward the bar or the composer fades out into an empty band that holds the scroll button,
		     so neither a cut line nor the button sits on text; the thread's bottom padding clears the band -->
		<div class="pointer-events-none absolute inset-x-0 bottom-0 h-16 bg-gradient-to-t from-surface-base from-[40px]" />
		<Button
			v-if="!stick && !blank"
			class="absolute bottom-1.5 left-1/2 z-10 -translate-x-1/2 rounded-full shadow-md"
			icon="lucide-arrow-down"
			variant="outline"
			tooltip="Scroll to bottom"
			@click="toBottom"
		/>
		<AddToChat :within="scroller" />
	</div>
</template>

<script setup>
import { computed, inject, nextTick, onBeforeUnmount, onMounted, provide, reactive, ref, watch } from "vue"
import { Button } from "frappe-ui"

import { approvalToAnswer, buildItems, formatDuration, panelIds } from "../transcript.js"
import AddToChat from "./AddToChat.vue"
import ApprovalCard from "./ApprovalCard.vue"
import ArtifactCard from "./ArtifactCard.vue"
import ArtifactGroup from "./ArtifactGroup.vue"
import AssistantText from "./AssistantText.vue"
import CopyButton from "./CopyButton.vue"
import LoadingState from "./LoadingState.vue"
import ThoughtStep from "./ThoughtStep.vue"
import ToolGroup from "./ToolGroup.vue"
import TurnFold from "./TurnFold.vue"
import UserBubble from "./UserBubble.vue"

const flow = inject("flow")
const conversation = computed(() => flow.state.conversation)
const expandedTurnKeys = ref(new Set())
// rows (tool calls, thoughts) the user has open, by id
const openPanels = reactive(new Set())
provide("openPanels", openPanels)
const openLatest = computed(() => Boolean(flow.options.openTurn?.()))
const items = computed(() => buildItems(conversation.value, expandedTurnKeys.value, openPanels, { openLatest: openLatest.value }))

const blank = computed(() => !items.value.length && !conversation.value.running && !conversation.value.liveLabel)
const loading = computed(() => blank.value && flow.state.loading)
// the running turn ends above the steered bubbles waiting below it
const turnEnd = computed(() => items.value.length - (conversation.value.steering?.length ?? 0))

// thoughts stack like they do inside a group
function tightGap(i) {
	return items.value[i - 1]?.kind === "thinking" && items.value[i]?.kind === "thinking" ? "-mt-3" : ""
}

const approval = computed(() => {
	const pending = approvalToAnswer(conversation.value)
	const index = pending?.calls.findIndex((call) => !(call.id in pending.answers)) ?? -1
	if (index === -1) return null
	return { call: pending.calls[index], position: index + 1, total: pending.calls.length }
})

const working = computed(() => conversation.value.running || conversation.value.sending?.length > 0)
const liveLabel = computed(() =>
	conversation.value.running && !conversation.value.steering?.length ? conversation.value.liveLabel || "Working" : "Working",
)

// elapsed time of the turn at work, from its user message
const now = ref(Date.now())
let ticker = null
watch(
	working,
	(on) => {
		clearInterval(ticker)
		now.value = Date.now()
		if (on) ticker = setInterval(() => (now.value = Date.now()), 1000)
	},
	{ immediate: true },
)
onBeforeUnmount(() => clearInterval(ticker))
const elapsed = computed(() => {
	const ts = items.value.findLast((item) => item.kind === "user")?.entry?.ts
	if (!Number.isFinite(ts)) return ""
	const ms = Math.max(0, now.value - ts * 1000)
	return ms < 1000 ? "" : formatDuration(ms)
})

const partialVersion = computed(() => {
	const partial = conversation.value.partial
	const tail = partial[partial.length - 1]
	const streamedLength = tail?.text?.length ?? tail?.thinking?.length ?? 0
	const ready = partial.filter((b) => b.type === "tool_call" && b.arguments != null).length
	return `${partial.length}:${tail?.type ?? ""}:${tail?.id ?? ""}:${streamedLength}:${ready}`
})

const scroller = ref(null)
const stick = ref(true)
let lastScrollTop = 0
let atBottom = true

function onScroll() {
	const el = scroller.value
	if (!el) return
	const distance = el.scrollHeight - el.scrollTop - el.clientHeight
	const goingUp = el.scrollTop < lastScrollTop
	lastScrollTop = el.scrollTop
	atBottom = distance < 4
	// any upward scroll unsticks; only reaching the bottom re-sticks
	if (distance < 4) stick.value = true
	else if (goingUp) stick.value = false
}

// a clicked button, link or summary takes no focus, so a closing dialog can't scroll the list back to it
function onMouseDown(event) {
	if (event.target.closest("button, a[href], summary")) event.preventDefault()
}

// collapsing rows, resizing the column or what the host adds at the end moves no scroll position;
// a view that sat on the bottom stays there
const thread = ref(null)
const end = ref(null)
let resizeObserver = null
onMounted(() => {
	if (typeof ResizeObserver === "undefined") return
	resizeObserver = new ResizeObserver((entries) => {
		const el = scroller.value
		if (!el) return
		const resized = (target) => entries.some((entry) => entry.target === target)
		if (stick.value && ((atBottom && resized(el)) || resized(end.value))) el.scrollTop = el.scrollHeight
		atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 4
		if (atBottom) stick.value = true
	})
	watch(
		thread,
		(el) => {
			resizeObserver.disconnect()
			resizeObserver.observe(scroller.value)
			if (el) resizeObserver.observe(el)
			if (end.value) resizeObserver.observe(end.value)
		},
		{ immediate: true },
	)
})
onBeforeUnmount(() => resizeObserver?.disconnect())

function toBottom() {
	const el = scroller.value
	if (!el) return
	el.scrollTo({ top: el.scrollHeight, behavior: "smooth" })
	stick.value = true
}

function toggleTurn(item) {
	const { turnKey, expanded } = item
	const next = new Set(expandedTurnKeys.value)
	if (expanded) {
		next.delete(turnKey)
		// an open row holds its turn unfolded, so folding closes the turn's rows
		for (const id of items.value.filter((i) => i.turnKey === turnKey).flatMap(panelIds)) openPanels.delete(id)
	} else next.add(turnKey)
	expandedTurnKeys.value = next
	if (expanded) return
	void nextTick(() => {
		const fold = scroller.value?.querySelector(`[data-turn-fold="${CSS.escape(turnKey)}"]`)
		fold?.nextElementSibling?.scrollIntoView({ block: "nearest", behavior: "smooth" })
	})
}

// your own message belongs at the live end of the thread
const sendingCount = computed(
	() => (conversation.value.sending?.length ?? 0) + (conversation.value.steering?.length ?? 0),
)
watch(sendingCount, (count, before) => {
	if (count > before) stick.value = true
})

watch(
	() => [
		conversation.value.entries.length,
		sendingCount.value,
		partialVersion.value,
		working.value,
		approval.value?.call.id,
		openLatest.value,
	],
	async () => {
		if (!stick.value) return
		await nextTick()
		const el = scroller.value
		if (el) el.scrollTop = el.scrollHeight
	},
)

watch(
	() => flow.state.sessionId,
	() => {
		stick.value = true
		expandedTurnKeys.value = new Set()
		openPanels.clear()
	},
)
</script>
