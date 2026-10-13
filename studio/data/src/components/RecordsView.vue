<template>
	<div class="flex flex-col">
		<div v-if="loading && !rows.length" class="flex flex-col gap-3 p-4">
			<Skeleton v-for="i in 8" :key="i" class="h-8 w-full rounded-4" />
		</div>
		<NoRecords v-else-if="!rows.length" />
		<div v-else class="flex min-h-0 flex-1 flex-col px-3 pb-3 pt-3">
			<div ref="frame" class="relative flex min-h-0 flex-1 flex-col">
				<ListView
					:columns="columns"
					:rows="rows"
					row-key="name"
					class="!w-full shrink-0"
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
					<ListRows />
					<template #cell="{ column, item }">
						<span v-if="column.field?.fieldtype === 'Color' && item" class="flex min-w-0 items-center gap-2">
							<span class="size-3 shrink-0 rounded-full border border-outline-gray-2" :style="{ background: String(item) }" />
							<span class="truncate text-sm text-ink-gray-5">{{ item }}</span>
						</span>
						<Tooltip v-else-if="column.field?.fieldtype === 'Link' && titles[`${column.field.options}::${item}`]" :text="String(item)">
							<span class="block truncate text-sm text-ink-gray-7">{{ titles[`${column.field.options}::${item}`] }}</span>
						</Tooltip>
						<span v-else-if="column.field && NUMERIC.has(column.field.fieldtype)" class="block truncate text-right text-sm tabular-nums text-ink-gray-7">
							{{ formatValue(column.field, item) || "—" }}
						</span>
						<span v-else class="block truncate text-sm" :class="column.key === 'name' ? 'text-ink-gray-8' : 'text-ink-gray-7'">
							{{ column.field ? formatValue(column.field, item) : item }}
						</span>
					</template>
				</ListView>
			</div>
			<p v-if="rows.length < (doctype.count ?? 0)" class="px-2 pt-3 text-sm text-ink-gray-5">
				Latest {{ rows.length }} of {{ doctype.count?.toLocaleString() }}
			</p>
		</div>
	</div>
</template>

<script setup lang="ts">
import { useDebounceFn, useElementSize } from "@vueuse/core"
import { onListUpdate } from "@shell/realtime"
import { Skeleton, Tooltip } from "frappe-ui"
import { ListHeader, ListHeaderItem, ListRows, ListView } from "frappe-ui/experimental"
import { computed, onBeforeUnmount, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"

import { type DocField, type Row, getLinkTitles, getRecords } from "../api"
import { doctype, elementId, refreshCount } from "../doctype"
import { fieldIcon, fieldLabel, formatValue, hasValue } from "../fields"
import NoRecords from "./NoRecords.vue"

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
// columns share the panel's width, the title most; the fields whose minimums do not fit stay in the form
const NUMERIC = new Set(["Int", "Float", "Currency", "Percent"])
const NARROW = new Set([...NUMERIC, "Check", "Time", "Color", "Rating"])
const sizeOf = (field: DocField): [number, number] => {
	if (field.fieldname === doctype.doc?.title_field) return [8, 1.5]
	if (NARROW.has(field.fieldtype)) return [5, 0.6]
	return [6, 1]
}
const grid = ([min, share]: [number, number]) => `minmax(${min}rem, ${share}fr)`
const all = computed(() => [
	naming.value
		? { key: "name", label: fieldLabel(naming.value), size: [8, 1.5] as [number, number], field: naming.value as DocField | null }
		: { key: "name", label: "ID", size: [6, 0.8] as [number, number], field: null },
	...listed.value.map((field) => ({
		key: field.fieldname!,
		label: fieldLabel(field),
		size: sizeOf(field),
		align: NUMERIC.has(field.fieldtype) ? "right" : undefined,
		field,
	})),
].map((column) => ({ ...column, width: grid(column.size) })))
// each column takes its minimum and a 1rem gap, the row 1rem of padding
const frame = ref<HTMLElement | null>(null)
const { width } = useElementSize(frame)
const columns = computed(() => {
	let room = width.value / 16 - 1
	return all.value.filter((column, index) => (room -= column.size[0] + 1) >= 0 || index === 0)
})

const rows = ref<Row[]>([])
const titles = ref<Record<string, string>>({})
const loading = ref(false)
async function load() {
	loading.value = true
	try {
		const records = await getRecords(doctype.name, ["name", ...listed.value.map((field) => field.fieldname!)])
		titles.value = await getLinkTitles(listed.value, records).catch(() => ({}))
		rows.value = records
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
