// The chart as its owner holds it: the document, the config being edited, the
// save. What the config produces is not here — the server derives the operations
// from it and runs them, and `chart_view` is where the rows come back.

import { reactive, toRefs, watch } from 'vue'
import { getUniqueId, safeJSONParse, wheneverChanges } from '../helpers'
import { GranularityType } from '../helpers/constants'
import useDocumentResource from '../helpers/resource'
import useQuery from '../query/query'
import { AXIS_CHARTS } from '../types/chart.types'
import { InsightsChartv3 } from '../types/workbook.types'
import { getLinkedQueries } from '../query/linked_queries'
import { invalidateChart, renameChartViews } from './chart_view'
import {
	configDimensions,
	ensureConfigSlots,
	normalizeChartConfig,
	resetChartConfig,
} from './helpers'

const charts = new Map<string, Chart>()

export default function useChart(name: string) {
	const key = String(name)
	const existingChart = charts.get(key)
	if (existingChart) return existingChart

	const chart = makeChart(name)
	charts.set(key, chart)
	return chart
}

function makeChart(name: string) {
	const chart = getChartResource(name)

	function updateGranularity(column_name: string, granularity: GranularityType) {
		configDimensions(chart.doc.config).forEach((dimension) => {
			if (dimension.dimension_name === column_name) {
				dimension.granularity = granularity
			}
		})
	}

	function getDependentQueries() {
		return [chart.doc.query, ...getLinkedQueries(chart.doc.query)]
	}

	function getDependentQueryColumns() {
		return getDependentQueries().map((q) => {
			const query = useQuery(q)
			query.ensureResult()
			return {
				group: query.doc.title,
				options: query.result.columnOptions.map((c) => {
					const sep = '`'
					const value = `${sep}${query.doc.name}${sep}.${sep}${c.value}${sep}`
					return {
						...c,
						value,
					}
				}),
			}
		})
	}

	function resetConfig() {
		// @ts-ignore
		chart.doc.config = resetChartConfig(chart.doc.config, chart.doc.chart_type)
	}

	// when chart type changes from axis to non-axis or vice versa reset the config
	watch(
		() => chart.doc.chart_type,
		(newType: string, oldType: string) => {
			if (!newType || newType === oldType) return
			const crossesAxisBoundary =
				oldType && AXIS_CHARTS.includes(newType) !== AXIS_CHARTS.includes(oldType)
			if (crossesAxisBoundary) {
				resetConfig()
			}
			ensureConfigSlots(chart.doc.config, newType)
		},
	)

	return reactive({
		...toRefs(chart),

		updateGranularity,
		resetConfig,

		getDependentQueries,
		getDependentQueryColumns,

	})
}

export type Chart = ReturnType<typeof makeChart>

const INITIAL_DOC: InsightsChartv3 = {
	doctype: 'Insights Chart v3',
	name: '',
	owner: '',
	title: '',
	description: '',
	info: '',
	workbook: '',
	query: '',
	chart_type: '',
	sort_order: 0,
	visibility: 'Private',
	visible_to_roles: [],
	run_as_owner: false,
	config: {} as InsightsChartv3['config'],
	operations: [],
	read_only: false,
}

function getChartResource(name: string) {
	const doctype = 'Insights Chart v3'
	const chart = useDocumentResource<InsightsChartv3>(doctype, name, {
		initialDoc: { ...INITIAL_DOC, name },
		enableAutoSave: true,
		disableLocalStorage: true,
		transform: transformChartDoc,
	})
	// A chart is inserted with the config its author already sees, which is the
	// normalized one. Send anything else and the answer comes back in a shape the
	// load normalizes differently — the document is dirty for being created, and
	// creating a chart costs a write and a second run of its data.
	chart.onBeforeInsert(() => {
		chart.doc.config = normalizeChartConfig(chart.doc.config, chart.doc.chart_type)
	})
	// Every card in this tab keeps its chart and rows until Refresh. The author's
	// own save is the exception: the author knows the chart changed, so the next
	// card that shows it fetches again.
	chart.onAfterSave(() => invalidateChart(String(chart.doc.name)))
	wheneverChanges(
		() => chart.doc.read_only,
		() => {
			if (chart.doc.read_only) {
				chart.autoSave = false
			}
		},
	)
	return chart
}

function transformChartDoc(doc: any) {
	doc.config = safeJSONParse(doc.config) || {}
	doc.operations = safeJSONParse(doc.operations) || []

	doc.config = normalizeChartConfig(doc.config, doc.chart_type)

	return doc
}

export function newChart() {
	const unsavedName = 'new-chart-' + getUniqueId()
	const chart = makeChart(unsavedName)
	// The page that opens next asks for the chart by the name the insert gave it,
	// and has to be handed this store. A second store for one chart writes the
	// document twice and runs its data twice, and the two disagree from the first
	// edit. The rows it already rendered move with it, or nothing invalidating the
	// saved chart would reach them.
	chart.onAfterInsert(() => {
		charts.set(String(chart.doc.name), chart)
		renameChartViews(unsavedName, String(chart.doc.name))
	})
	return chart
}
