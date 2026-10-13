<template>
	<div v-if="doc" class="flex flex-col gap-4 p-4">
		<FormControl
			type="select"
			label="Title field"
			:model-value="doc.title_field || ''"
			:options="titleOptions"
			@update:model-value="(value: string) => change((doc) => Object.assign(doc, { title_field: value, show_title_field_in_link: value ? 1 : 0 }))"
		/>
		<Switch
			label="Track changes"
			:model-value="Boolean(doc.track_changes)"
			@update:model-value="(on: boolean) => change((doc) => (doc.track_changes = on ? 1 : 0))"
		/>
	</div>
</template>

<script setup lang="ts">
import { FormControl, Switch } from "frappe-ui"
import { computed } from "vue"

import { change, doctype } from "../doctype"
import { fieldLabel } from "../fields"

const TITLE_TYPES = new Set(["Data", "Link", "Select", "Small Text", "Text", "Dynamic Link"])

const doc = computed(() => doctype.doc)
const titleOptions = computed(() => [
	{ label: "None", value: "" },
	...(doc.value?.fields ?? [])
		.filter((field) => field.fieldname && TITLE_TYPES.has(field.fieldtype))
		.map((field) => ({ label: fieldLabel(field), value: field.fieldname! })),
])
</script>
