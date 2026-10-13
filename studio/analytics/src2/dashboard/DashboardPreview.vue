<script setup lang="ts">
import { useDashboardBuilder } from './builder'
import useDashboard from './dashboard'
import DashboardBody from './DashboardBody.vue'
import DashboardItem from './DashboardItem.vue'
import EditableGridLayout from './EditableGridLayout.vue'

// One dashboard, by name, as the editor shows it: the grid is always editable.
// A press selects a tile, a drag moves it, its corner resizes it. The store's
// `selectedIndex` is the selection the editor's toolbar and chat read.
const props = defineProps<{ name: string }>()

const dashboard = useDashboardBuilder(props.name)
const store = useDashboard(props.name)
</script>

<template>
	<DashboardBody
		class="h-full"
		:dashboard="dashboard"
		:grid="EditableGridLayout"
		:cell="DashboardItem"
		@background-press="store.selectedIndex = undefined"
	/>
</template>
