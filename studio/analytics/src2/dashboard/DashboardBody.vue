<script setup lang="ts">
import { computed, type Component } from 'vue'
import { __ } from '../translation'
import type { BreakpointKey, Layout } from '../types/workbook.types'
import type { DashboardAction, DashboardView } from './view'

// A dashboard's content on every page that shows one: the grid, with its filter
// cells, and the loading, Not Found and error states.
//
// It renders no header. Each page renders its own header above this. The SPA
// page and the builder read the actions through a template ref, and the island
// reports the same list to its host. Nothing here checks which page it is on.
//
// The page gives this a box of fixed size, and this fills it. So the grid
// scrolls and the page around it does not.
const props = defineProps<{
	// `useDashboardView` on a view page, `useDashboardBuilder` in the builder
	dashboard: DashboardView
	// A reader gets a read-only grid, so the drag-and-resize code never loads on
	// a page that cannot use it
	grid: Component
	cell: Component
}>()

// a press on the grid's empty space, which clears the editor's selection
const emit = defineEmits<{ backgroundPress: [] }>()

// Every action a reader may take, in one list. A page only renders it.
const actions = computed<DashboardAction[]>(() => [
	{ label: __('Refresh'), icon: 'refresh-cw', onClick: () => props.dashboard.refresh(true) },
])

// A page reads this through a template ref. The island reads the same ref and
// reports the actions to its host.
defineExpose({ actions })
</script>

<template>
	<div class="flex h-full w-full flex-col overflow-hidden">
		<div
			v-if="dashboard.notFound"
			class="flex w-full flex-1 items-center justify-center p-4 text-p-base text-ink-gray-5"
		>
			{{ __('Dashboard not found') }}
		</div>

		<div
			v-else-if="dashboard.failed"
			class="flex w-full flex-1 items-center justify-center p-4 text-p-base text-ink-gray-5"
		>
			{{ __('Could not load the dashboard. Refresh to try again.') }}
		</div>

		<div v-else-if="dashboard.loading" class="flex-1 p-4">
			<div class="h-8 w-64 animate-pulse rounded-4 bg-surface-gray-2" />
		</div>

		<!-- The only scroller on the page. An empty dashboard keeps it, because a
		     chart is dropped onto the grid here. -->
		<div v-else class="flex-1 overflow-y-auto p-2" @pointerdown.self="emit('backgroundPress')">
			<div
				v-if="!dashboard.items.length"
				class="flex h-full w-full items-center justify-center text-p-base text-ink-gray-5"
			>
				{{ __('This dashboard is empty') }}
			</div>

			<component
				:is="props.grid"
				v-else
				class="mx-auto h-fit w-full max-w-6xl"
				:breakpoint="dashboard.builder?.arranging"
				:class="dashboard.builder ? 'mb-[20rem] !select-none' : ''"
				:disabled="!dashboard.builder"
				:verticalCompact="dashboard.verticalCompact"
				:items="dashboard.items"
				:rules="dashboard.cellRules"
				@move="
					(key: BreakpointKey, layouts: Layout[], before: Layout[]) =>
						layouts && dashboard.builder?.moveItems(key, layouts, before)
				"
			>
				<template #item="{ index }">
					<component
						:is="props.cell"
						:dashboard="dashboard"
						:item="dashboard.items[index]"
						:index="index"
					/>
				</template>
			</component>
		</div>
	</div>
</template>
