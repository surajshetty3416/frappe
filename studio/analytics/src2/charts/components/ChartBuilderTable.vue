<script setup lang="ts">
import { inject, ref } from 'vue'
import ResultPane from '../../components/result_pane/ResultPane.vue'
import QueryDataTable from '../../query/components/QueryDataTable.vue'
import { SortDirection } from '../../types/query.types'
import { sortBy } from '../adapter/table'
import { Chart } from '../chart'
import { chartPreviewKey } from '../chart_preview'
import ViewDrillDown from '../drill/ViewDrillDown.vue'
import type { ChartSegmentClick } from '../drill/segment_click'

// The rows under a chart. A header click sorts the chart; a cell opens the
// rows behind it, the same drill a click on the chart opens.
const props = defineProps<{
	readOnly?: boolean
}>()

const chart = inject('chart') as Chart
const preview = inject(chartPreviewKey)!

const clicked = ref<ChartSegmentClick>()

function onSortChange(column_name: string, sort_order: SortDirection) {
	sortBy(chart.doc.config as any, column_name, sort_order)
}
</script>

<template>
	<!-- the pane keeps its height and the card above gives way: a footer cut in
	     half is broken chrome, a shorter chart is not -->
	<div
		v-if="chart.doc.chart_type != 'Table'"
		class="flex h-[18rem] flex-shrink-0 flex-col overflow-hidden"
	>
		<ResultPane :query="preview" no-find>
			<template #grid="{ rows, currentPage, pageSize }">
				<QueryDataTable
					:query="preview"
					:rows="rows"
					:current-page="currentPage"
					:page-size="pageSize"
					:enable-sort="!props.readOnly"
					:enable-drill-down="true"
					@segment-click="clicked = $event"
					:on-sort-change="onSortChange"
				/>
			</template>
		</ResultPane>
	</div>

	<!-- `v-if` unmounts it on close, so every drill starts from an empty stack -->
	<ViewDrillDown
		v-if="clicked"
		:subject="preview.drillSubject"
		:clicked="clicked"
		@close="clicked = undefined"
	/>
</template>
