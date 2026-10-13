<template>
	<Popover v-if="property.type === 'color'" side="bottom" align="start">
		<template #trigger>
			<Button variant="ghost" :tooltip="property.label">
				<span class="block size-4 rounded-full border border-outline-gray-2" :style="{ background: property.value || 'transparent' }" />
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
							class="block size-6 cursor-pointer rounded-md border border-outline-gray-2 hover:scale-110 transition-transform"
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
	<Tooltip v-else :text="property.label">
		<Select
			size="sm"
			variant="ghost"
			:placeholder="property.label"
			:model-value="property.value || null"
			:options="property.options ?? []"
			@update:model-value="(value) => property.set(String(value))"
		>
			<template #prefix><span :class="property.icon" class="size-4 text-ink-gray-5" /></template>
		</Select>
	</Tooltip>
</template>

<script setup lang="ts">
import { Button, Popover, Select, TextInput, Tooltip } from "frappe-ui"

import type { ElementProperty } from "../editor"

const props = defineProps<{ property: ElementProperty }>()

const SWATCHES = [
	"#ffffff", "#f5f5f4", "#d6d3d1", "#a8a29e", "#57534e", "#292524", "#171717", "#000000",
	"#fee2e2", "#fef3c7", "#dcfce7", "#dbeafe", "#ede9fe", "#fce7f3", "#ffedd5", "#ccfbf1",
	"#dc2626", "#d97706", "#16a34a", "#2563eb", "#7c3aed", "#db2777", "#ea580c", "#0d9488",
]

function pick(value: string, close: () => void) {
	const color = value.trim()
	if (color) props.property.set(color)
	close()
}
</script>
