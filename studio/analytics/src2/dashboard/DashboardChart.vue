<script setup lang="ts">
import { editorMode } from '@shell/editor'
import { Button, Tooltip } from 'frappe-ui'
import { SquareArrowOutUpRight } from 'lucide-vue-next'
import { computed } from 'vue'
import { rendersOwnCards } from '../charts/adapter'
import ChartRenderer from '../charts/components/ChartRenderer.vue'
import { __ } from '../translation'
import { useChartCell, type ChartCellProps } from './chart_cell'

// A chart tile in the editor. The chart is its own artifact, so the tile opens it.
const props = defineProps<ChartCellProps & { selected?: boolean }>()

const { read, reading, filtered, resetFilters } = useChartCell(props)

// a card that renders itself heads its title with a zero-height row, which fits the smallest control
const actionSize = computed(() =>
	read.value && rendersOwnCards(read.value.doc.chart_type) ? 'xs' : 'sm',
)

const chartRoute = computed(() =>
	props.item.chart ? props.dashboard.chartRoute?.(props.item.chart) : undefined,
)

// in Edit the shell draws hover, so the tile's own action waits for the selection, or hover would look like it
const editing = computed(() => editorMode.value === 'edit')
const showOpen = computed(() => Boolean(chartRoute.value) && (!editing.value || props.selected))
</script>

<template>
	<ChartRenderer
		:chart="read"
		:reading="reading"
		:filtered="filtered"
		hide-maximize
		:actions-revealed="editing && props.selected"
		@reset-filters="resetFilters"
	>
		<template v-if="showOpen" #hoverActions>
			<Tooltip :text="__('Open chart')">
				<Button variant="ghost" :size="actionSize" :route="chartRoute">
					<SquareArrowOutUpRight class="h-3.5 w-3.5 text-ink-gray-6" stroke-width="1.5" />
				</Button>
			</Tooltip>
		</template>
	</ChartRenderer>
</template>
