<template>
	<div class="group flex flex-col items-end gap-1">
		<div class="flow-prose w-full rounded-6 bg-surface-gray-1 px-3 py-2 text-ink-gray-8">
			<div v-if="imageTiles.length" class="flex flex-wrap gap-1.5" :class="hasText || chips.length ? 'mb-2' : ''">
				<button
					v-for="item in imageTiles"
					:key="item.id"
					type="button"
					class="size-16 flex-none cursor-zoom-in overflow-hidden rounded-4 border border-outline-gray-2 bg-surface-white"
					:title="item.name"
					@click="viewer = item"
				>
					<img :src="previews[item.id]" :alt="item.name" class="size-full object-cover" />
				</button>
			</div>
			<div v-if="chips.length" class="flex flex-wrap items-center gap-1.5" :class="hasText ? 'mb-2' : ''">
				<span
					v-for="chip in chips"
					:key="chip.key"
					class="flex h-7 max-w-full items-center gap-1.5 rounded-4 border border-outline-gray-2 bg-surface-white px-2"
					:title="chip.title"
				>
					<span :class="chip.icon" class="size-4 flex-none text-ink-gray-5" />
					<span class="truncate text-sm text-ink-gray-8">{{ chip.label }}</span>
				</span>
			</div>
			<div v-if="hasText" ref="textEl" class="whitespace-pre-wrap break-words" :class="expanded ? '' : 'line-clamp-[12]'"
				><div v-if="quotes.length" class="flex flex-col gap-2" :class="body ? 'mb-2' : ''"
					><blockquote v-for="(quote, i) in quotes" :key="i" class="border-l-2 border-outline-gray-2 pl-3 text-ink-gray-6">{{
						quote
					}}</blockquote></div
				><span v-for="(part, i) in parts" :key="i" :class="{ 'text-ink-blue-6': part.skill }">{{ part.text }}</span></div
			>
			<button
				v-if="clampable"
				type="button"
				class="mt-1 text-sm text-ink-gray-5 hover:text-ink-gray-8"
				@click="expanded = !expanded"
			>
				{{ expanded ? "Show less" : "Show more" }}
			</button>
		</div>
		<span class="flow-hover-reveal flex items-center gap-1">
			<span v-if="time" class="text-sm text-ink-gray-5">{{ time }}</span>
			<CopyButton :text="text" />
		</span>
		<ImageViewer v-if="viewer" :src="previews[viewer.id]" :alt="viewer.name" @close="viewer = null" />
	</div>
</template>

<script setup>
import { computed, inject, onBeforeUnmount, onMounted, ref } from "vue"

import { formatTime, invokedSkills, skillSegments, splitQuotes, userAttachments, userText } from "../transcript.js"
import CopyButton from "./CopyButton.vue"
import ImageViewer from "./ImageViewer.vue"

const props = defineProps({ entry: { type: Object, required: true } })
const flow = inject("flow")
const time = computed(() => formatTime(props.entry.ts))
const text = computed(() => userText(props.entry))
const attachments = computed(() => userAttachments(props.entry))
const quoted = computed(() => splitQuotes(text.value))
const body = computed(() => quoted.value.body)
const quotes = computed(() => quoted.value.quotes)
const hasText = computed(() => !!body.value || quotes.value.length > 0)
// skill commands stay blue, as in the composer; a bubble still sending knows only the catalog
const parts = computed(() => {
	const sending = props.entry.seq == null ? (flow.state.skills ?? []).map((skill) => skill.name) : []
	return skillSegments(body.value, invokedSkills(props.entry) ?? sending)
})
// images show as previews; other files as chips
const imageTiles = computed(() => attachments.value.filter((item) => previews.value[item.id]))
const chips = computed(() =>
	attachments.value
		.filter((item) => !previews.value[item.id])
		.map((item) => ({
			key: item.id,
			icon: item.kind === "image" ? "lucide-image" : "lucide-file-text",
			label: item.name,
			title: item.name,
		})),
)

const previews = ref({}) // attachment id → object URL of the stored image
const viewer = ref(null)
let disposed = false

onMounted(() => {
	const sid = flow.state.sessionId
	if (!sid) return
	for (const item of attachments.value) {
		if (item.kind !== "image" || !item.id) continue
		flow.attachmentPreview(sid, item.id).then((url) => {
			if (!url) return
			if (disposed) URL.revokeObjectURL(url)
			else previews.value[item.id] = url
		})
	}
})
onBeforeUnmount(() => {
	disposed = true
	for (const url of Object.values(previews.value)) URL.revokeObjectURL(url)
})

// show the toggle only when the 12-line clamp actually truncated
const expanded = ref(false)
const textEl = ref(null)
const clampable = ref(false)
onMounted(() => {
	const el = textEl.value
	clampable.value = !!el && el.scrollHeight > el.clientHeight + 1
})
</script>
