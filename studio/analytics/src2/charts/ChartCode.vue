<script setup lang="ts">
import { Button } from 'frappe-ui'
import { computed, ref, watch } from 'vue'
import Code from '../components/Code.vue'
import { waitUntil } from '../helpers'
import useQuery from '../query/query'
import { __ } from '../translation'
import useChart from './chart'
import useChartPreview from './chart_preview'

// The chart's Code view: the query behind it, as SQL, or as Python when the query
// is a script. Cmd+Enter runs it, saves it and redraws the chart.
//
// A query built step by step shows the SQL it compiles to. Running an edit of it
// makes it a SQL query, because the steps cannot be read back from SQL.
const props = defineProps<{ name: string }>()

const chart = useChart(props.name)
const preview = useChartPreview(chart)

const query = ref<ReturnType<typeof useQuery>>()
const code = ref('')
const running = ref(false)

const isScript = computed(() => Boolean(query.value?.doc.is_script_query))

waitUntil(() => !chart.pending && Boolean(chart.doc.query)).then(async () => {
	const q = useQuery(chart.doc.query)
	await waitUntil(() => !q.pending)
	query.value = q
	if (q.doc.is_script_query) {
		code.value = q.getCodeOperation()?.code || ''
	} else if (q.doc.is_native_query) {
		code.value = (q.getSQLOperation() as any)?.raw_sql || ''
	} else {
		q.ensureResult()
		await waitUntil(() => Boolean(q.result.executedSQL))
		code.value = q.result.executedSQL
	}
})

// the data source a builder query reads from, for when its SQL is run as SQL
function dataSource() {
	const operations = query.value?.doc.operations || []
	const first = operations[0] as any
	if (first?.type === 'sql') return first.data_source
	if (first?.type === 'source') return first.table.data_source
}

async function run() {
	const q = query.value
	if (!q || running.value) return
	running.value = true
	try {
		if (q.doc.is_script_query) {
			q.setCode({ code: code.value })
		} else {
			q.doc.is_native_query = true
			q.doc.is_builder_query = false
			q.setSQL({ raw_sql: code.value, data_source: dataSource() }, true)
		}
		await q.save()
		await preview.load(true)
	} finally {
		running.value = false
	}
}

watch(
	() => props.name,
	() => (query.value = undefined),
)
</script>

<template>
	<div
		class="flex h-full w-full flex-col gap-2"
		@keydown.meta.enter.prevent="run"
		@keydown.ctrl.enter.prevent="run"
	>
		<div class="flex items-center justify-between">
			<span class="text-p-sm text-ink-gray-5">
				{{ isScript ? __('Python') : __('SQL') }}
			</span>
			<Button
				:label="__('Run')"
				icon-left="lucide-play"
				:loading="running"
				:disabled="!query"
				@click="run"
			/>
		</div>
		<div class="flex min-h-0 flex-1 overflow-hidden rounded-4 border">
			<Code v-if="query" :key="String(isScript)" v-model="code" :language="isScript ? 'python' : 'sql'" />
		</div>
	</div>
</template>
