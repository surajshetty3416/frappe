<script setup lang="ts">
import { watchDebounced } from '@vueuse/core'
import { computed, provide } from 'vue'
import LoadingOverlay from '../components/LoadingOverlay.vue'
import { waitUntil } from '../helpers'
import useChart from './chart'
import useChartPreview, { chartPreviewKey } from './chart_preview'
import ChartBuilderTable from './components/ChartBuilderTable.vue'
import ChartRenderer from './components/ChartRenderer.vue'

// One chart, by name, as the editor shows it: the chart with its rows under it.
// The config being edited is what renders, so a change shows before it saves.
const props = defineProps<{ name: string }>()

const chart = useChart(props.name)
provide('chart', chart)

const preview = useChartPreview(chart)
provide(chartPreviewKey, preview)
// for a user who cannot write the chart, the preview runs the stored chart
const readOnly = computed(() => preview.doc.can_write === false)

// the first render separately, so opening a chart does not wait out the debounce
waitUntil(() => !chart.pending).then(() => preview.load())
watchDebounced(
	() => [chart.doc.query, chart.doc.chart_type, chart.doc.config],
	() => !chart.pending && preview.load(),
	{ deep: true, debounce: 500 },
)
</script>

<template>
	<div class="relative flex h-full w-full flex-col gap-3 overflow-hidden px-4 pb-4 pt-3">
		<LoadingOverlay v-if="chart.pending" />
		<div class="flex min-h-0 flex-1 items-center justify-center">
			<ChartRenderer :chart="preview" hide-maximize />
		</div>
		<ChartBuilderTable v-if="preview.result.executedSQL" :read-only="readOnly" />
	</div>
</template>
