<script setup lang="ts">
import { Button } from 'frappe-ui'
import { computed } from 'vue'
import { waitUntil } from '../helpers'
import dayjs from '../helpers/dayjs'
import useQuery from '../query/query'
import { __ } from '../translation'
import useChart from './chart'
import useChartPreview from './chart_preview'

// The chart's Details drawer: the query behind it, where it reads from, when it
// last fetched, and what it means.
const props = defineProps<{ name: string }>()

const chart = useChart(props.name)
const preview = useChartPreview(chart)
// mounted on its own, the drawer still shows when the chart last fetched
waitUntil(() => !chart.pending).then(() => preview.load())
const query = computed(() => (chart.doc.query ? useQuery(chart.doc.query) : undefined))

const source = computed(() => {
	const operations = query.value?.doc.operations || []
	const first = operations[0] as any
	if (first?.type === 'source') {
		const table = first.table
		return table.type === 'query' ? table.query_name : table.table_name
	}
	if (first?.type === 'sql') return first.data_source
	if (first?.type === 'code') return __('Python script')
})

const lastFetched = computed(() =>
	preview.executedAt ? dayjs(preview.executedAt).fromNow() : undefined,
)

const rows = computed(() => [
	{ label: __('Query'), value: query.value?.doc.title || chart.doc.query || '—' },
	{ label: __('Source'), value: source.value || '—' },
	{ label: __('Last fetched'), value: lastFetched.value || '—' },
])
</script>

<template>
	<div class="flex flex-col gap-3">
		<div v-for="row in rows" :key="row.label" class="flex items-center justify-between gap-2">
			<span class="text-p-sm text-ink-gray-5">{{ row.label }}</span>
			<span class="truncate text-p-sm text-ink-gray-8">{{ row.value }}</span>
		</div>
		<Button
			:label="__('Refresh')"
			icon-left="lucide-refresh-cw"
			:loading="preview.executing"
			@click="preview.load(true)"
		/>
		<FormControl
			type="textarea"
			:label="__('Description')"
			:placeholder="__('What this chart shows')"
			:modelValue="chart.doc.description ?? ''"
			@update:modelValue="chart.doc.description = $event"
		/>
	</div>
</template>
