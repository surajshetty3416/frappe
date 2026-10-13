<template>
	<div class="flex flex-col gap-4 p-4">
		<FormControl
			type="select"
			label="Page size"
			:model-value="state.doc?.page_size || 'A4'"
			:options="SIZES"
			@update:model-value="(size: string) => set('page_size', size)"
		/>
	</div>
</template>

<script setup lang="ts">
import type { OutputState, SetField } from "@web/output/outputEditor"
import { FormControl } from "frappe-ui"

defineProps<{ state: OutputState; set: SetField }>()

const SIZES = [
	{ label: "A4, 210 × 297 mm", value: "A4" },
	{ label: "A5, 148 × 210 mm", value: "A5" },
	{ label: "A6, 105 × 148 mm", value: "A6" },
	{ label: "Letter, 216 × 279 mm", value: "Letter" },
]
</script>
