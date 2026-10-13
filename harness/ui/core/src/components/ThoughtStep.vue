<template>
	<div>
		<component
			:is="expandable ? 'button' : 'div'"
			:type="expandable ? 'button' : undefined"
			class="-mx-1.5 flex w-fit select-none items-center gap-2 rounded-4 px-1.5 py-1 text-sm text-ink-gray-5"
			:class="expandable ? 'transition-colors duration-150 ease-out hover:bg-surface-gray-2 hover:text-ink-gray-7' : ''"
			:aria-expanded="expandable ? open : undefined"
			@click="expandable && (open = !open)"
		>
			<span class="lucide-brain size-4 flex-none" />
			<span :class="live ? 'flow-shimmer' : ''">{{ label }}</span>
			<span
				v-if="expandable"
				class="lucide-chevron-right size-3.5 flex-none transition-transform duration-150 ease-out"
				:class="open ? 'rotate-90' : ''"
			/>
		</component>

		<div v-if="open && expandable" class="mb-1 ml-2 mt-1 border-l border-outline-gray-2 pl-4">
			<div ref="panelEl" class="max-h-[260px] overflow-y-auto" @scroll="onPanelScroll">
				<MarkdownContent :text="block.thinking" class="text-sm leading-relaxed text-ink-gray-5" />
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from "vue"

import { usePanelOpen } from "../panels.js"
import { formatDuration } from "../transcript.js"
import MarkdownContent from "./MarkdownContent.vue"

const props = defineProps({
	id: { type: String, required: true },
	block: { type: Object, required: true },
	// this thought's chunks are still streaming in
	live: { type: Boolean, default: false },
})

const open = usePanelOpen(() => props.id)

// the open panel follows streamed text while the user is at its bottom
const panelEl = ref(null)
let panelPinned = false
const atPanelBottom = (el) => el.scrollHeight - el.scrollTop - el.clientHeight < 8
function onPanelScroll() {
	if (panelEl.value) panelPinned = atPanelBottom(panelEl.value)
}
watch(panelEl, (el) => {
	if (!el) return
	panelPinned = atPanelBottom(el)
	el.parentElement.scrollIntoView({ block: "nearest", behavior: "smooth" })
})
watch(
	() => props.block.thinking,
	async () => {
		if (!panelPinned) return
		await nextTick()
		const el = panelEl.value
		if (el) el.scrollTop = el.scrollHeight
	},
)

const expandable = computed(() => !!props.block.thinking)
const label = computed(() => {
	if (props.live) return "Thinking"
	const seconds = props.block.seconds
	return Number.isFinite(seconds) ? `Thought for ${formatDuration(Math.max(1, seconds) * 1000)}` : "Thought"
})
</script>
