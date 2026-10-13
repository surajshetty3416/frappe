<template>
	<div class="flex flex-col">
		<Teleport defer to="#data-view-actions">
			<span class="truncate text-sm text-ink-gray-5">{{ fields.length }} fields</span>
			<Button v-if="editable" icon-left="lucide-plus" label="Add field" @click="addField" />
		</Teleport>

		<div class="min-h-0 flex-1 overflow-y-auto px-3 pb-6 pt-3">
			<div :class="GRID" class="h-8 rounded-4 bg-surface-gray-2 px-2 text-sm text-ink-gray-5">
				<span />
				<span>Label</span>
				<span>Type</span>
				<span>Options</span>
				<span>Required</span>
				<span />
			</div>
			<Draggable v-model="fields" :item-key="rowKey" handle="[data-drag-handle]" :animation="150" :disabled="!editable" ghost-class="opacity-40">
				<template #item="{ element: field }">
					<div :class="GRID" class="group min-h-11 border-b border-outline-gray-1 px-2 py-1.5">
						<span data-selection-ui data-drag-handle class="flex h-7 cursor-grab items-center text-ink-gray-4 hover:text-ink-gray-6">
							<span v-if="editable" class="lucide-grip-vertical size-4" />
						</span>
						<div :data-element="elementId(field)" class="flex min-w-0 items-center gap-2 py-1">
							<span :class="fieldIcon(field.fieldtype)" class="size-4 shrink-0 text-ink-gray-5" />
							<span class="flex min-w-0 flex-col">
								<span data-text class="truncate text-base" :class="field.label ? 'text-ink-gray-8' : 'text-ink-gray-5'">{{ fieldLabel(field) }}</span>
								<span class="truncate font-mono text-xs text-ink-gray-5">{{ field.fieldname }}</span>
							</span>
						</div>
						<div data-selection-ui class="min-w-0">
							<Select
								v-if="editable"
								class="w-full"
								:model-value="field.fieldtype"
								:options="typeOptions(field.fieldtype)"
								@update:model-value="(value) => set(field, 'fieldtype', value)"
							/>
							<span v-else class="text-base text-ink-gray-7">{{ field.fieldtype }}</span>
						</div>
						<div data-selection-ui class="min-w-0">
							<template v-if="optionsKind(field.fieldtype) && editable">
								<TextInput
									v-if="optionsKind(field.fieldtype) === 'choices'"
									:model-value="choicesText(field)"
									placeholder="One, Two, Three"
									@change="(event: Event) => setChoices(field, (event.target as HTMLInputElement).value)"
								/>
								<Select
									v-else
									class="w-full"
									:model-value="field.options || null"
									:options="targetOptions(field)"
									:placeholder="optionsKind(field.fieldtype) === 'table' ? 'Rows of…' : 'Links to…'"
									@update:model-value="(value) => set(field, 'options', value)"
								/>
							</template>
							<span v-else class="block truncate text-base text-ink-gray-7">{{ (field.options || "").replace(/\n/g, ", ") }}</span>
						</div>
						<div data-selection-ui class="flex h-7 items-center">
							<Checkbox
								v-if="!isLayout(field)"
								:model-value="Boolean(field.reqd)"
								:disabled="!editable"
								@update:model-value="(value) => set(field, 'reqd', value ? 1 : 0)"
							/>
						</div>
						<div data-selection-ui class="flex justify-end">
							<Button
								v-if="editable"
								variant="ghost"
								icon="lucide-trash-2"
								tooltip="Remove field"
								class="opacity-0 group-hover:opacity-100 focus-visible:opacity-100"
								@click="removeField(field)"
							/>
						</div>
					</div>
				</template>
			</Draggable>
		</div>
	</div>
</template>

<script setup lang="ts">
import { Button, Checkbox, Select, TextInput } from "frappe-ui"
import { computed } from "vue"
import Draggable from "vuedraggable"

import type { DocField } from "../api"
import { change, doctype, editable, elementId } from "../doctype"
import { fieldIcon, fieldLabel, fieldTypes, isLayout, optionsKind } from "../fields"
import { doctypeNames } from "../names"

const GRID = "grid grid-cols-[20px_minmax(0,1.3fr)_minmax(0,1fr)_minmax(0,1.2fr)_72px_32px] items-center gap-3"

const fields = computed({
	get: () => doctype.doc?.fields ?? [],
	set: (ordered: DocField[]) => change((doc) => (doc.fields = ordered)),
})
const rowKey = (field: DocField) => field.name ?? `new-${field.idx}`

const typeOptions = (current: string) => {
	const types = fieldTypes()
	return (types.includes(current) ? types : [current, ...types]).map((type) => ({ label: type, value: type }))
}
const targetOptions = (field: DocField) => {
	const names = optionsKind(field.fieldtype) === "table" ? doctypeNames.tables : doctypeNames.links
	const all = field.options && !names.includes(field.options) ? [field.options, ...names] : names
	return all.map((name) => ({ label: name, value: name }))
}

const set = (field: DocField, key: "fieldtype" | "options" | "reqd", value: unknown) =>
	change(() => Object.assign(field, { [key]: value }))

const choicesText = (field: DocField) => (field.options || "").split("\n").filter(Boolean).join(", ")
function setChoices(field: DocField, text: string) {
	const options = text
		.split(",")
		.map((choice) => choice.trim())
		.filter(Boolean)
		.join("\n")
	if (options !== (field.options || "")) set(field, "options", options)
}

function addField() {
	const labels = new Set(fields.value.map((field) => field.label))
	let label = "New field"
	for (let n = 2; labels.has(label); n++) label = `New field ${n}`
	change((doc) => doc.fields.push({ label, fieldtype: "Data" }))
}

const removeField = (field: DocField) => change((doc) => (doc.fields = doc.fields.filter((other) => other !== field)))
</script>
