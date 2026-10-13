<script setup lang="ts">
import ChartView from '../ChartView.vue'
import type { ChartRead } from '../chart_view'

// A chart the person can change: a sort on it is saved to the chart.
const props = defineProps<{
	chart?: ChartRead
	reading?: string
	hideMaximize?: boolean
	actionsRevealed?: boolean
	/** Whether the reader narrowed these rows, and can take that back. */
	filtered?: boolean
}>()

const emit = defineEmits<{
	resetFilters: []
}>()
</script>

<template>
	<ChartView
		:chart="props.chart"
		:reading="props.reading"
		:hide-maximize="props.hideMaximize"
		:actions-revealed="props.actionsRevealed"
		:filtered="props.filtered"
		:readonly="false"
		@reset-filters="emit('resetFilters')"
	>
		<template v-if="$slots.actions" #actions="{ expanded }">
			<slot name="actions" :expanded="expanded" />
		</template>
		<template v-if="$slots.hoverActions" #hoverActions>
			<slot name="hoverActions" />
		</template>
	</ChartView>
</template>
