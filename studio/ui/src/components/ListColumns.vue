<template>
	<div class="flex flex-col gap-2">
		<p class="text-xs font-medium text-ink-gray-5">Column widths</p>
		<div v-for="(width, index) in columns" :key="index" class="flex items-center gap-2">
			<span class="w-28 shrink-0 truncate text-sm text-ink-gray-7">{{ headers[index] || `Column ${index + 1}` }}</span>
			<TextInput
				class="flex-1"
				size="sm"
				:model-value="width"
				placeholder="1fr"
				@change="(event: Event) => setWidth(index, (event.target as HTMLInputElement).value)"
			/>
		</div>
	</div>
</template>

<script setup lang="ts">
import { TextInput } from "frappe-ui"
import { computed } from "vue"

import type Block from "@ui/utils/block"

// A List's column widths as CSS grid tracks, named by its header cells
const props = defineProps<{ block: Block }>()

const columns = computed<string[]>(() => {
	const value = props.block.getProp("columns")
	return Array.isArray(value) ? value.map(String) : []
})
const headers = computed(() => {
	const header = props.block.children.find((child) => child.componentName === "ListHeader")
	return (header?.children ?? []).map((cell) =>
		cell.children
			.map((child) => child.getProp("text"))
			.filter((text) => typeof text === "string")
			.join(" "),
	)
})

function setWidth(index: number, value: string) {
	const next = [...columns.value]
	next[index] = value.trim() || "1fr"
	props.block.setProp("columns", next)
}
</script>
