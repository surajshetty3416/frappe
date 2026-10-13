<template>
	<div>
		<component
			:is="expandable ? 'button' : 'div'"
			class="-mx-1.5 flex w-[calc(100%+0.75rem)] items-center gap-2 rounded-4 px-1.5 py-1 text-left text-sm"
			:class="expandable ? 'group hover:bg-surface-gray-2' : ''"
			@click="expandable && (open = !open)"
		>
			<span class="relative size-4 flex-none text-ink-gray-5">
				<span class="lucide-brain absolute inset-0 size-4" :class="open ? 'opacity-0' : expandable ? 'group-hover:opacity-0' : ''" />
				<span
					v-if="expandable"
					class="lucide-chevron-right absolute inset-0 size-4 transition-transform"
					:class="open ? 'rotate-90' : 'opacity-0 group-hover:opacity-100'"
				/>
			</span>
			<span class="flex-none" :class="live ? 'flow-shimmer' : 'text-ink-gray-6'">{{ live ? "Thinking" : "Thought" }}</span>
			<span class="min-w-0 flex-1 truncate text-ink-gray-5">{{ preview }}</span>
		</component>

		<div v-if="open && expandable" class="mb-1 ml-6 mt-1 border-l border-outline-gray-2 pl-3">
			<div ref="panelEl" class="max-h-[260px] overflow-y-auto" @scroll="onPanelScroll">
				<MarkdownContent :text="block.thinking" class="text-sm leading-relaxed text-ink-gray-5" />
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from "vue"

import { usePanelOpen } from "../panels.js"
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

const expandable = computed(() => !props.block.redacted && !!props.block.thinking)
const preview = computed(() => {
	if (props.block.redacted) return ""
	const line = (props.block.thinking ?? "").split("\n").find((l) => l.trim()) ?? ""
	// markdown syntax is noise at one-line size; the panel renders it fully
	return line
		.replace(/^#{1,6}\s+/, "")
		.replace(/\*\*([^*]+)\*\*/g, "$1")
		.replace(/__([^_]+)__/g, "$1")
		.replace(/\*([^*]+)\*/g, "$1")
		.replace(/`([^`]+)`/g, "$1")
		.replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
})
</script>
