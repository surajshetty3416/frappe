// The dashboard the editor shows. It loads the document resource instead of
// asking the view endpoints by name. Above the fetch, the page is the same.
//
// It is separate from `view.ts` for the same reason `chart_preview` is separate
// from `chart_view`: the editor imports the chart stores and forms, and an
// island must not bundle them.

import { computed, provide, reactive, watch } from 'vue'
import { appPath } from '../app_path'
import { waitUntil } from '../helpers'
import type { BreakpointKey, Layout } from '../types/workbook.types'
import useDashboard from './dashboard'
import { BASE_BREAKPOINT } from './grid_placement'
import {
	type DashboardInBuilder,
	type DashboardViewItem,
	type FilterState,
} from './view'

export function useDashboardBuilder(name: string): DashboardInBuilder {
	const dashboard = useDashboard(name)
	provide('dashboard', dashboard)

	const items = computed(() => dashboard.doc.items as DashboardViewItem[])

	// A card loads its rows after its chart loads, because the preview is built
	// from the chart's config. Every mount calls load, because the chart or its
	// query may have been saved while no card showed it. The read skips the load
	// if its request is unchanged.
	const watched = new Set<string>()
	function loadChart(chart_name: string) {
		const chart = dashboard.chartsByName[chart_name]
		waitUntil(() => Boolean(chart?.isloaded)).then(() => dashboard.refreshChart(chart_name))
		if (watched.has(chart_name) || !chart) return
		watched.add(chart_name)
		watch(
			() => JSON.stringify([chart.doc.chart_type, chart.doc.config]),
			() => dashboard.refreshChart(chart_name),
		)
	}

	return reactive({
		loading: computed(() => !dashboard.isloaded),
		notFound: false,
		failed: false,
		name: computed(() => dashboard.doc.name),
		title: computed(() => dashboard.doc.title),
		items,
		cellRules: computed(() => dashboard.cellRules),
		verticalCompact: computed(() => Boolean(dashboard.doc.vertical_compact_layout)),

		// The owner sees the defaults they set, not their last choice. A default
		// belongs to the document, and the owner is here to check it.
		filters: computed(() => dashboard.filterStates),
		setFilter: (filter_name: string, filter?: FilterState) =>
			dashboard.updateFilterState(filter_name, filter?.operator, filter?.value),
		// The values come from the linked chart, so a filter whose link is not
		// saved yet still lists them.
		filterValues: (filter_name: string, search_term?: string) => {
			const filter = dashboard.doc.items.find(
				(item) => item.type === 'filter' && item.filter_name === filter_name,
			)
			const linked = Object.keys((filter?.type === 'filter' && filter.links) || {})[0]
			if (!linked) return Promise.resolve([])
			return dashboard.getDistinctColumnValues(filter_name, search_term, linked)
		},
		filterRange: dashboard.getFilterColumnRange,
		cardFilters: computed(() => dashboard.cardFilters),
		setCardFilters: dashboard.setCardFilters,
		cardValues: (chart: string, column: string, search_term?: string) =>
			dashboard.getCardColumnValues(chart, column, search_term),
		cardRange: (chart: string, column: string) => dashboard.getCardColumnRange(chart, column),
		filtered: dashboard.cardIsFiltered,
		resetCardFilters: dashboard.resetCardFilters,
		chartView: dashboard.chartView,
		chartRoute: (chart: string) => appPath(`/charts/${chart}`),
		loadChart,
		refresh: dashboard.refresh,

		// The grid is always editable, at the widest breakpoint: that is the layout
		// every item has and the one the narrower ones derive from.
		builder: {
			arranging: BASE_BREAKPOINT.key,
			moveItems: (key: BreakpointKey, layouts: Layout[], before: Layout[]) =>
				dashboard.moveItems(key, layouts, before, dashboard.doc.vertical_compact_layout),
		},
	}) as DashboardInBuilder
}
