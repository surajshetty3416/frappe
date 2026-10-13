<script setup lang="ts">
import { computed } from 'vue'
import ColorInput from '../components/ColorInput.vue'
import { __ } from '../translation'
import {
	AXIS_CHARTS,
	CHARTS,
	type AxisChartConfig,
	type NumberChartConfig,
} from '../types/chart.types'
import useChart from './chart'
import useChartPreview from './chart_preview'
import ChartSortConfig from './components/ChartSortConfig.vue'
import NumberFormatFields from './components/NumberFormatFields.vue'

// A selected chart's properties: its type, how its numbers print, its sort and
// its color. The chart saves itself on each change, and every preview of it
// redraws. `reading` names the reading a Number tile shows; its color is that
// reading's own.
const props = defineProps<{ name: string; reading?: string }>()

const chart = useChart(props.name)
const preview = useChartPreview(chart)

const typeOptions = CHARTS.map((type) => ({ label: __(type), value: type }))

const isAxis = computed(() => AXIS_CHARTS.includes(chart.doc.chart_type))
const isNumber = computed(() => chart.doc.chart_type === 'Number')

// The Number reading the color belongs to: the one the tile names, else the first.
const readingIndex = computed(() => {
	const columns = (chart.doc.config as NumberChartConfig).number_columns || []
	const index = props.reading ? columns.findIndex((column) => column.id === props.reading) : 0
	return Math.max(index, 0)
})

const color = computed<string | undefined>({
	get() {
		if (isNumber.value) {
			const config = chart.doc.config as NumberChartConfig
			return config.number_column_options?.[readingIndex.value]?.color
		}
		if (isAxis.value) {
			return (chart.doc.config as AxisChartConfig).y_axis?.series?.[0]?.color?.[0]
		}
	},
	set(value) {
		if (isNumber.value) {
			const config = chart.doc.config as NumberChartConfig
			config.number_column_options ||= []
			const options = (config.number_column_options[readingIndex.value] ||= {})
			options.color = value || undefined
			return
		}
		const series = (chart.doc.config as AxisChartConfig).y_axis?.series?.[0]
		if (series) series.color = value ? [value] : undefined
	},
})
</script>

<template>
	<div class="flex flex-col gap-3">
		<FormControl
			type="select"
			:label="__('Type')"
			:options="typeOptions"
			:modelValue="chart.doc.chart_type"
			@update:modelValue="chart.doc.chart_type = $event"
		/>

		<div class="flex flex-col gap-1.5">
			<label class="text-xs text-ink-gray-5">{{ __('Number format') }}</label>
			<NumberFormatFields :config="chart.doc.config" />
		</div>

		<div v-if="chart.doc.chart_type !== 'Number'" class="flex flex-col gap-1.5">
			<label class="text-xs text-ink-gray-5">{{ __('Sort') }}</label>
			<ChartSortConfig
				v-model="chart.doc.config.order_by"
				:column-options="preview.result.columnOptions || []"
			/>
		</div>

		<div v-if="isNumber || isAxis" class="flex flex-col gap-1.5">
			<label class="text-xs text-ink-gray-5">{{ __('Color') }}</label>
			<ColorInput v-model="color" />
		</div>
	</div>
</template>
