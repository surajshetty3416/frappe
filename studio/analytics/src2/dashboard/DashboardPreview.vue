<script setup lang="ts">
import { editorMode } from '@shell/editor'
import { defineComponent, h } from 'vue'
import { useDashboardBuilder } from './builder'
import DashboardBody from './DashboardBody.vue'
import DashboardItem from './DashboardItem.vue'
import EditableGridLayout from './EditableGridLayout.vue'

// One dashboard, by name, as the editor shows it: the grid is editable in the
// shell's Edit mode. A drag moves a tile, its corner resizes it.
const props = defineProps<{ name: string }>()

const dashboard = useDashboardBuilder(props.name)

// Preview shows the dashboard as a reader gets it: no drag and no resize corners
const Grid = defineComponent({
	inheritAttrs: false,
	props: { disabled: Boolean },
	setup(gridProps, { attrs, slots }) {
		return () =>
			h(EditableGridLayout, { ...attrs, disabled: gridProps.disabled || editorMode.value === 'preview' }, slots)
	},
})
</script>

<template>
	<DashboardBody class="h-full" :dashboard="dashboard" :grid="Grid" :cell="DashboardItem" />
</template>
