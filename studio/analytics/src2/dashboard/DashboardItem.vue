<script setup lang="ts">
import { computed, inject } from 'vue'
import { WorkbookDashboardItem, WorkbookDashboardText } from '../types/workbook.types'
import { Dashboard } from './dashboard'
import DashboardChart from './DashboardChart.vue'
import DashboardFilter from './DashboardFilter.vue'
import DashboardItemActions from './DashboardItemActions.vue'
import DashboardText from './DashboardText.vue'
import type { DashboardCellProps } from './view'

// A grid cell in the editor: the card a reader sees, rendered from the config
// being edited. A press selects it; the grid around it moves and resizes it.
const props = defineProps<DashboardCellProps>()

// The page passes the item in the reader's shape, because both the view and
// the editor use that shape.
const item = computed(() => props.item as unknown as WorkbookDashboardItem)

const dashboard = inject('dashboard') as Dashboard

const selected = computed(() => dashboard.selectedIndex === props.index)

function editText() {
	if (item.value.type === 'text') dashboard.editingTextIndex = props.index
}
</script>

<template>
	<div
		class="group relative flex h-full w-full p-2"
		@pointerdown.capture="dashboard.selectedIndex = props.index"
		@dblclick="editText"
	>
		<div
			class="flex h-full w-full justify-start rounded-4 outline-offset-2"
			:class="
				selected
					? 'outline outline-2 outline-outline-gray-4'
					: 'group-hover:outline group-hover:outline-1 group-hover:outline-outline-gray-3'
			"
		>
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
		<DashboardItemActions
			v-if="selected"
			class="absolute top-0 right-0"
			:item-index="props.index"
		/>
	</div>
</template>
