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
					:model-value="property.value"
					placeholder="#000000"
					@keydown.enter="pick(($event.target as HTMLInputElement).value, close)"
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
				<TextInput
					size="sm"
					:model-value="property.value"
					:placeholder="property.placeholder"
					@keydown.enter="pick(($event.target as HTMLInputElement).value, close, true)"
				/>
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
import { computed } from "vue"
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

// a text property may be cleared; a color may not
function pick(value: string, close: () => void, empty = false) {
	const next = value.trim()
	if (next || empty) props.property.set(next)
	close()
}
</script>
