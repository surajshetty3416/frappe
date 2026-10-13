<template>
	<div class="flex flex-col gap-2">
		<button
			type="button"
			class="flex w-full max-w-sm items-center gap-3 rounded-6 border border-outline-gray-2 bg-surface-base px-3 py-2.5 text-left transition-colors hover:bg-surface-gray-1"
			:aria-expanded="open"
			@click="open = !open"
		>
			<span class="grid size-8 flex-none place-items-center rounded-4 bg-surface-gray-2 text-ink-gray-6">
				<span :class="icon" class="size-4" />
			</span>
			<span class="min-w-0 flex-1">
				<span class="block truncate text-base font-medium text-ink-gray-8">{{ title }}</span>
				<span class="block truncate text-sm text-ink-gray-5">{{ layers }}</span>
			</span>
			<span :class="open ? 'lucide-chevron-up' : 'lucide-chevron-down'" class="size-4 flex-none text-ink-gray-4" />
		</button>
		<ArtifactCard v-for="artifact in open ? artifacts : []" :key="artifact.route" :artifact="artifact" />
	</div>
</template>

<script setup>
import { computed, inject, ref } from "vue"

import ArtifactCard from "./ArtifactCard.vue"

// the artifacts of a turn that changed many, as one row that opens to their cards
const props = defineProps({ artifacts: { type: Array, required: true } })
const flow = inject("flow")
const open = ref(false)

// "Changed 1 Dashboard and 4 Charts"
const title = computed(() => {
	const counts = new Map()
	for (const { label } of props.artifacts) counts.set(label, (counts.get(label) ?? 0) + 1)
	const parts = [...counts].map(([label, count]) => `${count} ${label}${count === 1 ? "" : "s"}`)
	const last = parts.pop()
	return `Changed ${parts.length ? `${parts.join(", ")} and ${last}` : last}`
})
const layers = computed(() =>
	[...new Set(props.artifacts.map((artifact) => flow.options.artifactLayer?.(artifact) ?? artifact.label))].join(", "),
)
const icon = computed(() => {
	const icons = new Set(props.artifacts.map((artifact) => flow.options.artifactIcon?.(artifact) ?? "lucide-file"))
	return icons.size === 1 ? [...icons][0] : "lucide-layers"
})
</script>
