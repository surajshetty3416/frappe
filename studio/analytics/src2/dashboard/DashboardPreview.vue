<script setup lang="ts">
import { useDashboardBuilder } from './builder'
import DashboardBody from './DashboardBody.vue'
import DashboardItem from './DashboardItem.vue'
import EditableGridLayout from './EditableGridLayout.vue'

// One dashboard, by name, as the editor shows it: the grid is always editable.
// A drag moves a tile, its corner resizes it.
const props = defineProps<{ name: string }>()

const dashboard = useDashboardBuilder(props.name)
</script>

<template>
	<DashboardBody
		class="h-full"
		:dashboard="dashboard"
		:grid="EditableGridLayout"
		:cell="DashboardItem"
	/>
</template>
