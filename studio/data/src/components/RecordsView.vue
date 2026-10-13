<template>
	<div class="flex flex-col">
		<div v-if="loading && !rows.length" class="flex flex-col gap-3 p-4">
			<Skeleton v-for="i in 8" :key="i" class="h-8 w-full rounded-4" />
		</div>
		<NoRecords v-else-if="!rows.length" />
		<div v-else class="flex min-h-0 flex-1 flex-col px-3 pb-3 pt-3">
			<div ref="frame" class="relative flex min-h-0 flex-1 flex-col">
				<span ref="probe" aria-hidden="true" class="invisible absolute text-sm" />
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
							<span class="block truncate text-sm text-ink-gray-7">{{ cellText(column.field, item) }}</span>
						</Tooltip>
						<span v-else-if="column.field && NUMERIC.has(column.field.fieldtype)" class="block truncate text-right text-sm tabular-nums text-ink-gray-7">
							{{ cellText(column.field, item) || "—" }}
						</span>
						<span v-else class="block truncate text-sm" :class="column.key === 'name' ? 'text-ink-gray-8' : 'text-ink-gray-7'">
							{{ cellText(column.field, item) }}
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
const NUMERIC = new Set(["Int", "Float", "Currency", "Percent"])
const all = computed(() => [
	naming.value
		? { key: "name", label: fieldLabel(naming.value), field: naming.value as DocField | null }
		: { key: "name", label: "ID", field: null },
	...listed.value.map((field) => ({
		key: field.fieldname!,
		label: fieldLabel(field),
		align: NUMERIC.has(field.fieldtype) ? "right" : undefined,
		field,
	})),
])
type Column = (typeof all.value)[number]

const cellText = (field: DocField | null, item: unknown) => {
	if (!field) return String(item ?? "")
	if (field.fieldtype === "Link") return titles.value[`${field.options}::${item}`] || String(item ?? "")
	return formatValue(field, item)
}

// each column is as wide as its header and widest value, up to a cap past which a long value truncates;
// columns join in field order while they fit, and the room left spreads across them
const MAX_WIDTH = 240
const HEADER_ICON = 20
const GAP = 16
const PADDING = 16
const frame = ref<HTMLElement | null>(null)
const probe = ref<HTMLElement | null>(null)
const { width } = useElementSize(frame)
const needs = computed(() => {
	const style = probe.value && getComputedStyle(probe.value)
	const context = style && document.createElement("canvas").getContext("2d")
	if (!context) return {} as Record<string, number>
	context.font = `${style.fontWeight} ${style.fontSize} ${style.fontFamily}`
	context.letterSpacing = style.letterSpacing
	const swatch = 20
	return Object.fromEntries(
		all.value.map((column) => {
			const values = rows.value.map((row) => {
				const text = cellText(column.field, row[column.key])
				return context.measureText(text).width + (column.field?.fieldtype === "Color" && text ? swatch : 0)
			})
			const header = context.measureText(column.label).width + HEADER_ICON
			return [column.key, Math.min(MAX_WIDTH, Math.ceil(Math.max(header, ...values)) + 1)]
		})
	)
})
const columns = computed(() => {
	let used = PADDING - GAP
	const shown: Column[] = []
	for (const [index, column] of all.value.entries()) {
		const need = needs.value[column.key] ?? 0
		if (index > 0 && used + GAP + need > width.value) continue
		used += GAP + need
		shown.push(column)
	}
	const spare = Math.max(0, width.value - used) / shown.length
	return shown.map((column) => ({ ...column, width: `${(needs.value[column.key] ?? 0) + spare}px` }))
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
