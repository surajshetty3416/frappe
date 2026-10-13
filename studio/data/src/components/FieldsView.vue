<template>
	<div class="flex flex-col">
		<div class="min-h-0 flex-1 overflow-y-auto px-3 pb-6 pt-3">
			<div :class="grid" class="h-8 rounded-4 bg-surface-gray-2 px-2 text-sm text-ink-gray-5">
				<span v-if="editable" />
				<span>Label</span>
				<span>Type</span>
				<span>Options</span>
				<span>Required</span>
			</div>
			<Draggable
				v-model="fields"
				:item-key="rowKey"
				handle="[data-drag-handle]"
				:animation="150"
				:disabled="!editable"
				ghost-class="opacity-40"
			>
				<template #item="{ element: field }">
					<div
						v-if="BREAKS.has(field.fieldtype)"
						:class="grid"
						class="group h-8 border-b border-outline-gray-1 bg-surface-gray-1 px-2 text-xs uppercase text-ink-gray-5"
					>
						<span v-if="editable" data-selection-ui data-drag-handle class="flex h-full cursor-grab items-center text-ink-gray-4 hover:text-ink-gray-6">
							<span class="lucide-grip-vertical size-4" />
						</span>
						<span :data-element="elementId(field)" class="col-span-4 truncate">{{ field.label || field.fieldtype }}</span>
					</div>
					<div v-else :data-element="elementId(field)" :class="grid" class="group h-11 border-b border-outline-gray-1 px-2">
						<span v-if="editable" data-selection-ui data-drag-handle class="flex h-7 cursor-grab items-center text-ink-gray-4 hover:text-ink-gray-6">
							<span class="lucide-grip-vertical size-4" />
						</span>
						<div class="flex min-w-0 items-center gap-2 py-1">
							<span :class="fieldIcon(field.fieldtype)" class="size-4 shrink-0 text-ink-gray-5" />
							<span class="flex min-w-0 flex-col">
								<span data-text class="truncate text-sm" :class="field.label ? 'text-ink-gray-8' : 'text-ink-gray-5'">{{ fieldLabel(field) }}</span>
								<span class="truncate font-mono text-xs text-ink-gray-5">{{ field.fieldname }}</span>
							</span>
						</div>
						<template v-if="editable && doctype.selected === elementId(field)">
							<div data-selection-ui class="min-w-0">
								<Select
									class="w-full"
									:model-value="field.fieldtype"
									:options="typeOptions(field.fieldtype)"
									@update:model-value="(value) => set(field, 'fieldtype', value)"
								/>
							</div>
							<div data-selection-ui class="min-w-0">
								<Popover v-if="optionsKind(field.fieldtype) === 'choices'" side="bottom" align="start" @update:open="(open: boolean) => (open ? draftOf(field) : commitChoices(field))">
									<template #trigger>
										<Button class="w-full max-w-40 !justify-between" icon-right="lucide-chevron-down">
											<span class="min-w-0 truncate" :class="choices(field).length ? '' : 'text-ink-gray-4'">{{ choices(field).join(", ") || "Add options" }}</span>
										</Button>
									</template>
									<template #default>
										<div class="w-60 p-2">
											<p class="px-0.5 pb-1.5 text-xs text-ink-gray-5">One option per line</p>
											<Textarea v-model="choicesDraft[field.fieldname!]" :rows="5" autofocus />
										</div>
									</template>
								</Popover>
								<Select
									v-else-if="optionsKind(field.fieldtype)"
									class="w-full"
									:model-value="field.options || null"
									:options="targetOptions(field)"
									:placeholder="optionsKind(field.fieldtype) === 'table' ? 'Rows of…' : 'Links to…'"
									@update:model-value="(value) => set(field, 'options', value)"
								/>
							</div>
							<div data-selection-ui class="flex h-7 items-center">
								<Checkbox :model-value="Boolean(field.reqd)" @update:model-value="(value) => set(field, 'reqd', value ? 1 : 0)" />
							</div>
						</template>
						<template v-else>
							<span class="truncate text-sm text-ink-gray-7">{{ field.fieldtype }}</span>
							<span class="truncate text-sm text-ink-gray-7">{{ choices(field).join(", ") }}</span>
							<span v-if="field.reqd" class="lucide-check size-4 text-ink-gray-5" />
							<span v-else class="text-sm text-ink-gray-4">–</span>
						</template>
					</div>
				</template>
			</Draggable>
		</div>
	</div>
</template>

<script setup lang="ts">
import { Button, Checkbox, Popover, Select, Textarea } from "frappe-ui"
import { computed, reactive } from "vue"
import Draggable from "vuedraggable"

import type { DocField } from "../api"
import { change, doctype, editable, elementId } from "../doctype"
import { fieldIcon, fieldLabel, fieldTypes, isLayout, optionsKind } from "../fields"
import { doctypeNames } from "../names"

// read-only DocTypes cannot reorder, so they drop the grip column
const grid = computed(() =>
	editable.value
		? "grid grid-cols-[20px_minmax(0,1.3fr)_minmax(0,1fr)_minmax(0,1.2fr)_72px] items-center gap-3"
		: "grid grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)_minmax(0,1.2fr)_72px] items-center gap-3"
)
const BREAKS = new Set(["Section Break", "Column Break", "Tab Break"])

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

const choices = (field: DocField) => (field.options || "").split("\n").filter(Boolean)
const choicesDraft = reactive<Record<string, string>>({})
const draftOf = (field: DocField) => (choicesDraft[field.fieldname!] ??= choices(field).join("\n"))
function commitChoices(field: DocField) {
	const text = choicesDraft[field.fieldname!]
	delete choicesDraft[field.fieldname!]
	if (text === undefined) return
	const options = text
		.split("\n")
		.map((choice) => choice.trim())
		.filter(Boolean)
		.join("\n")
	if (options !== (field.options || "")) set(field, "options", options)
}
</script>
