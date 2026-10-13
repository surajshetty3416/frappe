<template>
	<div>
		<component
			:is="expandable ? 'button' : 'div'"
			class="-mx-1.5 flex w-[calc(100%+0.75rem)] items-center gap-2 rounded-4 px-1.5 py-1 text-left text-sm"
			:class="[expandable ? 'group' : '', live ? 'flow-tool-live' : '']"
			@click="expandable && (open = !open)"
		>
			<!-- the icon yields to a chevron on hover, and to the turned chevron while open -->
			<span class="relative size-4 flex-none text-ink-gray-5">
				<span :class="[icon, open ? 'opacity-0' : expandable ? 'group-hover:opacity-0' : '']" class="absolute inset-0 size-4" />
				<span
					v-if="expandable"
					class="lucide-chevron-right absolute inset-0 size-4 transition-transform"
					:class="open ? 'rotate-90' : 'opacity-0 group-hover:opacity-100'"
				/>
			</span>
			<span class="flex-none text-ink-gray-6">{{ label }}</span>
			<span class="min-w-0 flex-1 truncate text-ink-gray-5">{{ subject }}</span>
			<span v-if="stat" class="flex-none" :class="statClass">{{ stat }}</span>
		</component>

		<div v-if="open && expandable" ref="payloadEl" class="mb-1 mt-1 overflow-hidden rounded-4 border border-outline-gray-1 bg-surface-base">
			<div v-if="reasoning" class="max-h-[200px] overflow-y-auto border-b border-outline-gray-1 px-3 py-2 last:border-b-0">
				<MarkdownContent :text="reasoning" class="text-sm leading-relaxed text-ink-gray-5" />
			</div>
			<div v-if="meta.argsComponent && !resultView" class="border-b border-outline-gray-1">
				<component :is="meta.argsComponent" :arguments="args" />
			</div>
			<!-- a call the user denied or redirected -->
			<div v-if="decision" class="px-3 py-2">
				<div class="text-sm font-medium" :class="statClass">{{ decisionTitle }}</div>
				<div v-if="decision.user_feedback" class="mt-1 text-sm text-ink-gray-6">“{{ decision.user_feedback }}”</div>
			</div>
			<component :is="resultView" v-else-if="resultView" :arguments="args" :result="step.result" />
			<div v-else-if="step.result" class="relative">
				<CopyButton :text="output" class="absolute right-1 top-1" />
				<pre class="m-0 max-h-[200px] overflow-y-auto whitespace-pre-wrap break-words px-3 py-2 pr-9 font-mono text-xs leading-relaxed text-ink-gray-6">{{ output }}</pre>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, inject, ref, watch } from "vue"

import { usePanelOpen } from "../panels.js"
import { stepDecision, stepIcon, stepLabel, stepStat, stepSubject } from "../transcript.js"
import CopyButton from "./CopyButton.vue"
import MarkdownContent from "./MarkdownContent.vue"

const props = defineProps({
	step: { type: Object, required: true },
	// this step is the one executing right now: its row carries the sweep
	live: { type: Boolean, default: false },
})

const open = usePanelOpen(() => props.step.call.id)
const flow = inject("flow", null)

// a host describes its own tools
const args = computed(() => props.step.call.arguments ?? props.step.call.args ?? {})
const meta = computed(() => flow?.options?.presentTool?.(props.step.call.name, args.value, props.step.result) ?? {})
const icon = computed(() => meta.value.icon ?? stepIcon(props.step.call.name))
const label = computed(() => meta.value.label ?? stepLabel(props.step.call.name))
const subject = computed(() => meta.value.subject ?? stepSubject(props.step.call))
const failed = computed(() => props.step.result?.is_error === true)
const output = computed(() => {
	const content = props.step.result?.content ?? ""
	return typeof content === "string" ? content : JSON.stringify(content, null, 2)
})

const decision = computed(() => stepDecision(props.step.result))
const decisionTitle = computed(
	() =>
		({
			denied: "Denied",
			cancelled: "Cancelled",
			redirect: "You asked for changes",
		})[decision.value?.status] ?? "",
)

const stat = computed(() => {
	if (props.step.aborted && !props.step.result) return "Stopped"
	const child = props.step.subagent
	if (child?.running && !props.step.result) return child.liveLabel ?? "Working"
	// what the user decided about the call outranks what the tool says about itself
	if (decision.value) return stepStat(props.step)
	return meta.value.stat || stepStat(props.step) || ""
})
const statClass = computed(() => {
	if (decision.value) return decision.value.status === "redirect" ? "text-ink-amber-6" : "text-ink-red-6"
	return failed.value ? "text-ink-red-6" : "text-ink-gray-4"
})

const resultView = computed(() =>
	meta.value.resultComponent && props.step.result && !failed.value && !decision.value ? meta.value.resultComponent : null,
)

// expanding near the bottom edge would reveal the payload off-screen
const payloadEl = ref(null)
watch(payloadEl, (el) => el?.scrollIntoView({ block: "nearest", behavior: "smooth" }))

// the short thought that led to the call
const reasoning = computed(() => props.step.reasoning?.thinking ?? "")

const expandable = computed(() => {
	if (failed.value || decision.value || reasoning.value) return true
	if (meta.value.expandable === false) return false
	if (meta.value.argsComponent) return true
	if (!props.step.result) return false
	return !!resultView.value || !!output.value
})
</script>
