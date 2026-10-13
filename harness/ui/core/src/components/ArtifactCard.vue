<template>
	<button
		type="button"
		class="flex w-full max-w-sm items-center gap-3 rounded-6 border border-outline-gray-2 bg-surface-base px-3 py-2.5 text-left transition-colors hover:bg-surface-gray-1"
		@click="flow.options.openArtifact?.(artifact)"
	>
		<span class="grid size-8 flex-none place-items-center rounded-4 bg-surface-gray-2 text-ink-gray-6">
			<span :class="icon" class="size-4" />
		</span>
		<span class="min-w-0 flex-1">
			<span class="block truncate text-base font-medium text-ink-gray-8">{{ artifact.title }}</span>
			<span class="block truncate text-sm text-ink-gray-5">{{ layer }}</span>
		</span>
		<span class="lucide-chevron-right size-4 flex-none text-ink-gray-4" />
	</button>
</template>

<script setup>
import { computed, inject } from "vue"

const props = defineProps({ artifact: { type: Object, required: true } })
const flow = inject("flow")

const icon = computed(() => flow.options.artifactIcon?.(props.artifact) ?? "lucide-file")
const layer = computed(() => flow.options.artifactLayer?.(props.artifact) ?? props.artifact.label)
</script>
