<script setup lang="ts">
import { computed, inject } from 'vue'
import { WorkbookDashboardItem, WorkbookDashboardText } from '../types/workbook.types'
import { Dashboard } from './dashboard'
import DashboardChart from './DashboardChart.vue'
import DashboardFilter from './DashboardFilter.vue'
import DashboardText from './DashboardText.vue'
import type { DashboardCellProps } from './view'

// A grid cell in the editor: the card a reader sees, rendered from the config
// being edited. A press selects it; the grid around it moves and resizes it.
// The shell draws its hover and selection, and finds it by `data-tile`.
const props = defineProps<DashboardCellProps>()

// The page passes the item in the reader's shape, because both the view and
// the editor use that shape.
const item = computed(() => props.item as unknown as WorkbookDashboardItem)

const dashboard = inject('dashboard') as Dashboard
</script>

<template>
	<div
		class="group relative flex h-full w-full p-2"
		@pointerdown.capture="dashboard.selectedIndex = props.index"
	>
		<div :data-tile="item.layout.i" class="flex h-full w-full justify-start rounded-4">
			<DashboardChart
				v-if="item.type == 'chart'"
				:item="props.item"
				:dashboard="props.dashboard"
			/>

			<DashboardText
				v-else-if="item.type === 'text'"
				:item="item as WorkbookDashboardText"
				:editing="dashboard.editingTextIndex === props.index"
				@done="dashboard.editingTextIndex = undefined"
			/>

			<DashboardFilter
				v-else-if="item.type === 'filter'"
				:item="props.item"
				:dashboard="props.dashboard"
			/>
		</div>
	</div>
</template>
