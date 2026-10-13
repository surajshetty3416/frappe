<template>
	<Popover v-if="property.type === 'color'" side="bottom" align="start">
		<template #trigger>
			<Button variant="ghost" :tooltip="property.label" :aria-label="property.label" class="!gap-1 !px-1.5">
				<span class="flex items-center gap-1">
					<span class="block size-4 rounded-full ring-1 ring-inset ring-outline-gray-2" :style="{ background: property.value || 'transparent' }" />
					<span class="lucide-chevron-down size-4 text-ink-gray-5" />
				</span>
			</Button>
		</template>
		<template #default="{ close }">
			<div data-layer="shell" class="w-[212px] p-2">
				<p class="px-0.5 pb-2 text-xs font-medium text-ink-gray-5">{{ property.label }}</p>
				<div class="grid grid-cols-8 gap-1">
					<Tooltip v-for="swatch in SWATCHES" :key="swatch" :text="swatch">
						<span
							role="option"
							:aria-selected="swatch === property.value"
							class="block size-6 cursor-pointer rounded-4 border border-outline-gray-2 hover:scale-110 transition-transform"
							:class="swatch === property.value ? 'ring-2 ring-outline-gray-4 ring-offset-1' : ''"
							:style="{ background: swatch }"
							@click="pick(swatch, close)"
						/>
					</Tooltip>
				</div>
				<TextInput
					class="mt-2"
					size="sm"
					placeholder="#000000"
					v-bind="draftInput(close)"
				/>
			</div>
		</template>
	</Popover>
	<Popover v-else-if="property.type === 'popover' && property.component" side="bottom" align="start">
		<template #trigger>
			<Button variant="ghost" :icon-left="property.icon" :label="property.value || property.label" />
		</template>
		<div data-selection-ui class="max-h-[60vh] w-[340px] overflow-y-auto p-3">
			<LayerComponent :mount="property.component" :layer="layer" />
		</div>
	</Popover>
	<FileUploader
		v-else-if="property.type === 'upload'"
		:file-types="property.accept"
		:private="false"
		@success="(file: { file_url: string }) => property.set(file.file_url)"
	>
		<template #default="{ uploading, progress, openFileSelector }">
			<Button
				variant="ghost"
				:icon="uploading ? undefined : property.icon"
				:label="uploading ? `${progress}%` : undefined"
				:tooltip="property.value ? `${property.label}: ${property.value.split('/').pop()}` : property.label"
				:aria-label="property.label"
				@click="openFileSelector"
			/>
		</template>
	</FileUploader>
	<Popover v-else-if="property.type === 'text'" side="bottom" align="start">
		<template #trigger>
			<Button variant="ghost" :icon="property.icon" :tooltip="property.value ? `${property.label}: ${property.value}` : property.label" :aria-label="property.label" />
		</template>
		<template #default="{ close }">
			<div data-layer="shell" data-selection-ui class="w-[280px] p-2">
				<p class="px-0.5 pb-2 text-xs font-medium text-ink-gray-5">{{ property.label }}</p>
				<TextInput size="sm" :placeholder="property.placeholder" v-bind="draftInput(close, true)" />
			</div>
		</template>
	</Popover>
	<!-- the property's name leads its value, or stands in for it, so it needs no tooltip -->
	<Select
		v-else
		size="sm"
		variant="ghost"
		:placeholder="property.label"
		:aria-label="property.label"
		:model-value="property.value || null"
		:options="property.options ?? []"
		@update:model-value="(value) => property.set(String(value))"
	>
		<template v-if="property.value" #prefix><span class="whitespace-nowrap text-ink-gray-5">{{ property.label }}</span></template>
	</Select>
</template>

<script setup lang="ts">
import { Button, FileUploader, Popover, Select, TextInput, Tooltip } from "frappe-ui"
import { computed, ref } from "vue"
import { useRoute } from "vue-router"

import type { ElementProperty } from "../editor"
import LayerComponent from "./LayerComponent.vue"

const props = defineProps<{ property: ElementProperty }>()
const route = useRoute()
const layer = computed(() => route.matched[0]?.meta.layer as string | undefined)

const SWATCHES = [
	"#ffffff", "#f5f5f4", "#d6d3d1", "#a8a29e", "#57534e", "#292524", "#171717", "#000000",
	"#fee2e2", "#fef3c7", "#dcfce7", "#dbeafe", "#ede9fe", "#fce7f3", "#ffedd5", "#ccfbf1",
	"#dc2626", "#d97706", "#16a34a", "#2563eb", "#7c3aed", "#db2777", "#ea580c", "#0d9488",
]

function pick(value: string, close: () => void) {
	props.property.set(value)
	close()
}

// a text property may be cleared, a color may not. The typed value outlives re-renders until Enter or blur commits it; Esc drops it
const draft = ref<string | null>(null)
function commitDraft(empty: boolean) {
	const next = draft.value?.trim()
	draft.value = null
	if (next !== undefined && next !== (props.property.value ?? "") && (next || empty)) props.property.set(next)
}
function draftInput(close: () => void, empty = false) {
	return {
		modelValue: draft.value ?? props.property.value ?? "",
		"onUpdate:modelValue": (value: string) => (draft.value = value),
		onKeydown: (event: KeyboardEvent) => {
			if (event.key === "Enter") {
				// closing hands focus back to the trigger, which the same Enter would click open again
				event.preventDefault()
				commitDraft(empty)
				close()
			} else if (event.key === "Escape") draft.value = null
		},
		onBlur: () => commitDraft(empty),
	}
}
</script>
