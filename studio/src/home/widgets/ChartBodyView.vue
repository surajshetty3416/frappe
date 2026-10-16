<template>
	<ChartView :chart="shown" v-slot="{ chart, onSegmentClick }">
		<div v-if="chart.doc.chart_type === 'Number'" class="grid h-full auto-cols-[240px] grid-flow-col gap-3">
			<ChartBody v-for="reading in numberReadings(chart.doc.config)" :key="reading" :chart="chart" :reading="reading" readonly />
		</div>
		<ChartBody v-else :chart="chart" readonly @segment-click="onSegmentClick" />
	</ChartView>
</template>

<script setup lang="ts">
import { numberReadings } from "@analytics/charts/adapter/number"
import ChartBody from "@analytics/charts/components/ChartBody.vue"
import { useChartView } from "@analytics/charts/chart_view"
import ChartView from "@analytics/charts/ChartView.vue"

// one saved chart, its body only; a number chart shows each reading as a dashboard cell that names
// it does, filling its share of the widget
const props = defineProps<{ chart: string }>()

const shown = useChartView(props.chart)
shown.load()
</script>
