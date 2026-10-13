<template>
	<div v-if="field.fieldtype === 'Check'" class="flex h-7 items-center">
		<Checkbox :model-value="Boolean(modelValue)" :disabled="readonly" @update:model-value="(value) => emit('update:modelValue', value ? 1 : 0)" />
	</div>
	<Select
		v-else-if="field.fieldtype === 'Select'"
		class="w-full"
		:model-value="(modelValue as string) || null"
		:options="choices"
		:disabled="readonly"
		placeholder="Choose…"
		@update:model-value="(value) => emit('update:modelValue', value)"
	/>
	<Combobox
		v-else-if="field.fieldtype === 'Link'"
		class="w-full"
		open-on-focus
		:model-value="(modelValue as string) || null"
		:options="links"
		:disabled="readonly"
		:placeholder="`Choose a ${field.options}…`"
		@focus="loadLinks"
		@update:open="(open: boolean) => open && loadLinks()"
		@update:model-value="(value) => emit('update:modelValue', value)"
	/>
	<FormControl
		v-else-if="DATE_TYPES[field.fieldtype]"
		:type="DATE_TYPES[field.fieldtype]"
		:model-value="modelValue"
		:disabled="readonly"
		@update:model-value="(value: unknown) => emit('update:modelValue', value)"
	/>
	<Textarea
		v-else-if="LONG_TEXT.has(field.fieldtype)"
		:model-value="(modelValue as string) ?? ''"
		:rows="3"
		:disabled="readonly"
		@update:model-value="(value) => emit('update:modelValue', value)"
	/>
	<div v-else-if="TABLE_TYPES.has(field.fieldtype)" class="rounded-4 border border-outline-gray-2 px-3 py-2 text-sm text-ink-gray-6">
		{{ rowsLabel }}
	</div>
	<div v-else class="flex items-center gap-2">
		<img
			v-if="field.fieldtype === 'Attach Image' && modelValue"
			:src="String(modelValue)"
			alt=""
			class="size-7 shrink-0 rounded-4 border border-outline-gray-1 object-cover"
		/>
		<TextInput
			class="flex-1"
			:type="NUMBER_TYPES.has(field.fieldtype) ? 'number' : 'text'"
			:model-value="(modelValue as string | number) ?? ''"
			:disabled="readonly || field.fieldtype === 'Read Only'"
			@update:model-value="(value) => emit('update:modelValue', NUMBER_TYPES.has(field.fieldtype) && value !== '' ? Number(value) : value)"
		>
			<template v-if="field.fieldtype === 'Color'" #prefix>
				<span class="block size-3 rounded-full border border-outline-gray-2" :style="{ background: String(modelValue || 'transparent') }" />
			</template>
		</TextInput>
	</div>
</template>

<script setup lang="ts">
import { Checkbox, Combobox, FormControl, Select, TextInput, Textarea, call } from "frappe-ui"
import { computed, ref } from "vue"

import type { DocField } from "../api"
import { TABLE_TYPES } from "../fields"

const props = defineProps<{ field: DocField; modelValue: unknown; readonly?: boolean }>()
const emit = defineEmits<{ "update:modelValue": [value: unknown] }>()

const DATE_TYPES: Record<string, "date" | "datetime" | "time"> = { Date: "date", Datetime: "datetime", Time: "time" }
const LONG_TEXT = new Set(["Small Text", "Text", "Long Text", "Text Editor", "Markdown Editor", "Code", "JSON", "HTML Editor"])
const NUMBER_TYPES = new Set(["Int", "Float", "Currency", "Percent"])

const choices = computed(() =>
	(props.field.options ?? "")
		.split("\n")
		.filter(Boolean)
		.map((option) => ({ label: option, value: option }))
)

// a linked record shows by its title when its DocType shows titles in links, as the desk does
const links = ref<{ label: string; value: string }[]>([])
let linksLoaded = false
async function loadLinks() {
	if (linksLoaded || !props.field.options) return
	linksLoaded = true
	const results: { value: string; label?: string }[] = await call("frappe.desk.search.search_link", {
		doctype: props.field.options,
		txt: "",
		page_length: 200,
	})
	links.value = results.map((result) => ({ label: result.label || result.value, value: result.value }))
}
if (props.field.fieldtype === "Link" && props.modelValue) {
	const value = String(props.modelValue)
	links.value = [{ label: value, value }]
	call("frappe.desk.search.get_link_title", { doctype: props.field.options, docname: value }).then((title: string) => {
		if (!linksLoaded && title) links.value = [{ label: title, value }]
	})
}

const rowsLabel = computed(() => {
	const rows = Array.isArray(props.modelValue) ? props.modelValue.length : 0
	return rows === 1 ? "1 row" : `${rows} rows`
})
</script>
