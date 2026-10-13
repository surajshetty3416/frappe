<template>
	<div class="flex flex-col">
		<Teleport defer to="#data-view-actions">
			<span v-if="rows.length < (doctype.count ?? 0)" class="truncate text-sm text-ink-gray-5">
				Latest {{ rows.length }} of {{ doctype.count?.toLocaleString() }}
			</span>
		</Teleport>

		<div v-if="loading && !rows.length" class="flex flex-col gap-3 p-4">
			<Skeleton v-for="i in 8" :key="i" class="h-8 w-full rounded-4" />
		</div>
		<div v-else-if="!rows.length" class="flex flex-1 flex-col items-center justify-center px-6 text-center">
			<span class="lucide-rows-3 size-5 text-ink-gray-4" />
			<p class="mt-3 text-base font-medium text-ink-gray-8">No {{ doctype.name }} records yet</p>
			<p class="mt-1 max-w-sm text-p-sm text-ink-gray-5">Fill it with realistic demo data, or add the first record in the form.</p>
			<div data-selection-ui class="mt-4 flex gap-2">
				<Button v-if="editable" variant="solid" label="Demo data" icon-left="lucide-sparkles" @click="doctype.demoData = true" />
				<Button label="New record" icon-left="lucide-plus" @click="openForm('new')" />
			</div>
		</div>
		<div v-else class="min-h-0 flex-1 overflow-auto px-3 pb-6 pt-3">
			<ListView
				:columns="columns"
				:rows="rows"
				row-key="name"
				class="!w-full"
				:options="{ selectable: false, showTooltip: true, rowHeight: 36, onRowClick: (row: Row) => openForm(row.name) }"
			>
				<ListHeader class="sticky top-0 z-10">
					<ListHeaderItem
						v-for="column in columns"
						:key="column.key"
						:item="column"
						:data-element="column.field ? elementId(column.field) : undefined"
					>
						<span class="flex min-w-0 items-center gap-1.5">
							<span :class="column.field ? fieldIcon(column.field.fieldtype) : 'lucide-hash'" class="size-3.5 shrink-0" />
							<span data-text class="truncate">{{ column.label }}</span>
						</span>
					</ListHeaderItem>
				</ListHeader>
				<ListRows data-selection-ui />
				<template #cell="{ column, item }">
					<span v-if="column.field?.fieldtype === 'Color' && item" class="flex min-w-0 items-center gap-2">
						<span class="size-3 shrink-0 rounded-full border border-outline-gray-2" :style="{ background: String(item) }" />
						<span class="truncate text-sm text-ink-gray-5">{{ item }}</span>
					</span>
					<span v-else class="block truncate text-sm" :class="column.key === 'name' ? 'text-ink-gray-8' : 'text-ink-gray-7'">
						{{ column.field ? formatValue(column.field, item) : item }}
					</span>
				</template>
			</ListView>
		</div>
	</div>
</template>

<script setup lang="ts">
import { useDebounceFn } from "@vueuse/core"
import { onListUpdate } from "@shell/realtime"
import { Button, Skeleton } from "frappe-ui"
import { ListHeader, ListHeaderItem, ListRows, ListView } from "frappe-ui/experimental"
import { computed, onBeforeUnmount, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"

import { type DocField, type Row, getRecords } from "../api"
import { doctype, editable, elementId, refreshCount } from "../doctype"
import { fieldIcon, fieldLabel, formatValue, hasValue } from "../fields"

const route = useRoute()
const router = useRouter()

const MAX_COLUMNS = 6

// a record named by one of its fields shows that field as its ID
const naming = computed(() => {
	const fieldname = doctype.doc?.autoname?.startsWith("field:") ? doctype.doc.autoname.slice(6) : null
	return doctype.doc?.fields.find((field) => field.fieldname === fieldname) ?? null
})
// the fields the DocType lists, or its first ones when it names none
const listed = computed(() => {
	const fields = (doctype.doc?.fields ?? []).filter(
		(field) => hasValue(field) && field.fieldname && !field.hidden && field !== naming.value
	)
	const chosen = fields.filter((field) => field.in_list_view)
	return (chosen.length ? chosen : fields).slice(0, MAX_COLUMNS)
})
// the title takes the room; short values stay narrow
const NARROW = new Set(["Int", "Float", "Currency", "Percent", "Check", "Date", "Time", "Color", "Rating"])
const widthOf = (field: DocField) => {
	if (field.fieldname === doctype.doc?.title_field) return "minmax(12rem, 2fr)"
	if (NARROW.has(field.fieldtype)) return "minmax(6rem, 0.7fr)"
	return "minmax(10rem, 1fr)"
}
const columns = computed(() => [
	naming.value
		? { key: "name", label: fieldLabel(naming.value), width: "minmax(12rem, 2fr)", field: naming.value as DocField | null }
		: { key: "name", label: "ID", width: "7rem", field: null },
	...listed.value.map((field) => ({ key: field.fieldname!, label: fieldLabel(field), width: widthOf(field), field })),
])

const rows = ref<Row[]>([])
const loading = ref(false)
async function load() {
	loading.value = true
	try {
		rows.value = await getRecords(doctype.name, ["name", ...listed.value.map((field) => field.fieldname!)])
	} finally {
		loading.value = false
	}
}
watch(() => listed.value.map((field) => field.fieldname).join(), load, { immediate: true })

// records the assistant or anyone else adds show as they land
const refresh = useDebounceFn(() => Promise.all([load(), refreshCount()]), 500)
const stop = onListUpdate(doctype.name, refresh)
onBeforeUnmount(stop)

const openForm = (record: string) => router.replace({ query: { ...route.query, view: "form", record } })
</script>
