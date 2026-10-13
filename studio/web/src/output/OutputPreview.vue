<template>
	<div class="flex h-full flex-col bg-surface-gray-1">
		<!-- the switcher is the editor's own control, so the shell lets its clicks through -->
		<div data-selection-ui class="flex h-11 shrink-0 items-center gap-2 border-b border-outline-gray-1 bg-surface-base px-3 text-sm">
			<span class="text-ink-gray-5">Preview as</span>
			<Combobox
				v-if="state.records.length"
				trigger="button"
				size="sm"
				class="w-60"
				:model-value="state.record"
				:options="options"
				placeholder="Choose a record"
				@update:model-value="(value: string | null) => value && emit('pick', value)"
			/>
			<span v-else class="text-ink-gray-6">{{ state.target ? `No ${state.target} yet` : "" }}</span>
			<span v-if="state.page" class="ml-auto text-ink-gray-5">{{ pageLabel }}</span>
		</div>

		<div ref="viewport" class="relative min-h-0 flex-1 overflow-auto">
			<div v-if="state.error" class="m-6 rounded-6 border border-outline-red-2 bg-surface-red-1 p-4 text-sm text-ink-red-4">
				{{ state.error }}
			</div>

			<div v-else-if="state.page" class="flex justify-center py-8" :style="{ height: `${scaledHeight + 64}px` }">
				<div :style="{ width: `${scaledWidth}px`, height: `${scaledHeight}px` }">
					<div
						ref="host"
						data-output-preview
						class="origin-top-left bg-white"
						:style="{
							width: `${state.page.width}mm`,
							minHeight: `${state.page.height}mm`,
							padding: margins,
							transform: `scale(${scale})`,
							boxShadow: '0 0 0 1px var(--outline-gray-2)',
						}"
						v-html="state.html"
					/>
				</div>
			</div>

			<div v-else class="mx-auto flex max-w-[680px] flex-col gap-3 px-4 py-6">
				<div v-if="state.subject" class="rounded-6 border border-outline-gray-1 bg-surface-base px-4 py-3">
					<div class="text-xs text-ink-gray-5">Subject</div>
					<div class="mt-0.5 text-base font-medium text-ink-gray-8">{{ state.subject }}</div>
				</div>
				<div ref="host" data-output-preview class="overflow-hidden rounded-6 border border-outline-gray-1" v-html="state.html" />
			</div>

			<div v-if="state.loading && !state.html" class="absolute inset-0 grid place-items-center">
				<LoadingIndicator class="size-5 text-ink-gray-4" />
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { useElementSize } from "@vueuse/core"
import { Combobox, LoadingIndicator } from "frappe-ui"
import { computed, ref, watch } from "vue"

import type { OutputState } from "./outputEditor"

const props = defineProps<{ state: OutputState }>()
const emit = defineEmits<{ pick: [record: string]; host: [node: HTMLElement | null] }>()

const host = ref<HTMLElement | null>(null)
watch(host, (node) => emit("host", node), { immediate: true })

const options = computed(() =>
	props.state.records.map((record) => ({ label: record.title || record.name, value: record.name })),
)

const MM = 96 / 25.4
const viewport = ref<HTMLElement | null>(null)
const { width: viewportWidth, height: viewportHeight } = useElementSize(viewport)
// the page fits the panel, never past twice its size
const scale = computed(() => {
	const page = props.state.page
	if (!page || !viewportWidth.value) return 1
	const fit = Math.min((viewportWidth.value - 64) / (page.width * MM), (viewportHeight.value - 64) / (page.height * MM))
	return Math.max(0.3, Math.min(2, fit))
})
const scaledWidth = computed(() => (props.state.page?.width ?? 0) * MM * scale.value)
const scaledHeight = computed(() => (props.state.page?.height ?? 0) * MM * scale.value)
const margins = computed(() => {
	const m = props.state.page?.margins
	return m ? `${m.top}mm ${m.right}mm ${m.bottom}mm ${m.left}mm` : "0"
})
const pageLabel = computed(() => {
	const page = props.state.page
	return page ? `${page.size}, ${page.width} × ${page.height} mm` : ""
})
</script>
