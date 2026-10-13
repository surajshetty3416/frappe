<template>
	<div class="flex flex-col">
		<div v-if="loading" class="grid grid-cols-2 gap-4 p-5">
			<Skeleton v-for="i in 8" :key="i" class="h-12 w-full rounded-4" />
		</div>
		<div v-else-if="!record" class="flex flex-1 flex-col items-center justify-center px-6 text-center">
			<span class="lucide-square-pen size-5 text-ink-gray-4" />
			<p class="mt-3 text-base font-medium text-ink-gray-8">No record to show</p>
			<p class="mt-1 max-w-sm text-p-sm text-ink-gray-5">Add the first {{ doctype.name }} record, or ask for demo data.</p>
			<Button data-selection-ui class="mt-4" label="New record" icon-left="lucide-plus" @click="pick('new')" />
		</div>
		<div v-else class="min-h-0 flex-1 overflow-y-auto">
			<div data-selection-ui class="mx-auto flex max-w-3xl items-center gap-2 px-6 pt-4">
				<template v-if="isNew">
					<span class="flex-1 text-sm font-medium text-ink-gray-8">New {{ doctype.name }}</span>
					<Button v-if="options.length" label="Cancel" @click="pick(options[0].value)" />
					<Button variant="solid" label="Create" :loading="creating" @click="create" />
				</template>
				<template v-else>
					<Select class="w-auto min-w-0 max-w-80" :model-value="record" :options="options" @update:model-value="(value) => pick(String(value))">
						<template #trigger="{ selectedOption }">
							<span class="lucide-file-text size-4 shrink-0 text-ink-gray-5" />
							<span class="min-w-0 truncate text-ink-gray-8">{{ selectedOption?.label }}</span>
							<span v-if="selectedOption?.description" class="shrink-0 text-ink-gray-5">{{ selectedOption.description }}</span>
							<span class="lucide-chevron-down ml-auto size-4 shrink-0 text-ink-gray-4" />
						</template>
					</Select>
					<Button class="ml-auto" icon-left="lucide-plus" label="New record" @click="pick('new')" />
				</template>
			</div>
			<div class="mx-auto grid max-w-3xl grid-cols-2 gap-x-5 gap-y-4 px-6 py-5">
				<template v-for="(field, index) in layout" :key="field.fieldname ?? index">
					<h3
						v-if="field.fieldtype === 'Section Break'"
						class="col-span-2 border-t border-outline-gray-1 pt-4 text-sm font-medium text-ink-gray-8"
						:class="index === 0 ? 'border-t-0 pt-0' : ''"
					>
						{{ field.label }}
					</h3>
					<div
						v-else
						:data-element="elementId(field)"
						class="-m-2 flex min-w-0 flex-col gap-1.5 rounded-4 p-2"
						:class="WIDE.has(field.fieldtype) ? 'col-span-2' : ''"
					>
						<span class="flex items-center gap-1 text-sm text-ink-gray-6">
							<span data-text>{{ fieldLabel(field) }}</span>
							<span v-if="field.reqd" class="text-ink-red-4">*</span>
						</span>
						<div data-selection-ui>
							<RecordField :field="field" :model-value="draft[field.fieldname!]" @update:model-value="(value) => set(field, value)" />
						</div>
					</div>
				</template>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { useDebounceFn } from "@vueuse/core"
import { Button, Select, Skeleton, toast } from "frappe-ui"
import { computed, reactive, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"

import { type DocField, type Row, getRecord, getRecords, insertRecord, setValues } from "../api"
import { doctype, elementId, errorText, refreshCount, saving } from "../doctype"
import { TABLE_TYPES, fieldLabel, hasValue } from "../fields"
import RecordField from "./RecordField.vue"

const route = useRoute()
const router = useRouter()

const WIDE = new Set(["Small Text", "Text", "Long Text", "Text Editor", "Markdown Editor", "Code", "JSON", ...TABLE_TYPES])

// the fields a form shows, with sections as headings; column breaks are the grid's
const layout = computed(() =>
	(doctype.doc?.fields ?? []).filter(
		(field) => !field.hidden && field.fieldname && (hasValue(field) || TABLE_TYPES.has(field.fieldtype) || (field.fieldtype === "Section Break" && field.label))
	)
)

const options = ref<{ label: string; value: string; description?: string }[]>([])
const record = computed(() => {
	const wanted = route.query.record
	return typeof wanted === "string" && wanted ? wanted : (options.value[0]?.value ?? null)
})
const isNew = computed(() => record.value === "new")

const titleField = computed(() => doctype.doc?.title_field)
async function loadOptions() {
	const rows = await getRecords(doctype.name, ["name", ...(titleField.value ? [titleField.value] : [])], 50)
	options.value = rows.map((row) => ({
		label: titleField.value && row[titleField.value] ? `${row[titleField.value]}` : row.name,
		description: titleField.value && row[titleField.value] ? row.name : undefined,
		value: row.name,
	}))
	if (typeof route.query.record === "string" && !["new", ...rows.map((row) => row.name)].includes(route.query.record)) {
		options.value.unshift({ label: route.query.record, value: route.query.record })
	}
}

const draft = reactive<Record<string, unknown>>({})
const loading = ref(true)
async function load() {
	Object.keys(draft).forEach((key) => delete draft[key])
	if (!record.value) return
	if (isNew.value) {
		for (const field of layout.value) if (field.default !== undefined && field.default !== null) draft[field.fieldname!] = field.default
		return
	}
	Object.assign(draft, (await getRecord(doctype.name, record.value)) as Row)
}

loadOptions()
	.then(load)
	.catch((error) => toast.error(errorText(error)))
	.finally(() => (loading.value = false))
watch(record, (value, old) => value !== old && !loading.value && load())

const pick = (value: string) => router.replace({ query: { ...route.query, view: "form", record: value } })

// each change saves a moment after the last keystroke, as one write
const dirty = new Set<string>()
const save = useDebounceFn(async () => {
	if (isNew.value || !record.value || !dirty.size) return
	const values = Object.fromEntries([...dirty].map((key) => [key, draft[key]]))
	const name = record.value
	dirty.clear()
	try {
		await saving(() => setValues(doctype.name, name, values))
	} catch (error) {
		toast.error(errorText(error))
		await load()
	}
}, 600)

function set(field: DocField, value: unknown) {
	draft[field.fieldname!] = value
	if (isNew.value) return
	dirty.add(field.fieldname!)
	save()
}

const creating = ref(false)
async function create() {
	creating.value = true
	try {
		const made = await insertRecord(doctype.name, { ...draft })
		await loadOptions()
		refreshCount()
		pick(made.name)
	} catch (error) {
		toast.error(errorText(error))
	} finally {
		creating.value = false
	}
}
</script>
