import type { ElementProperty } from '@shell/editor'
import { paletteColors, useChartTokens } from 'frappe-ui/charts'
import { ref } from 'vue'
import { column } from '../query/helpers'
import { __ } from '../translation'
import {
	AXIS_CHARTS,
	CHARTS,
	type AxisChartConfig,
	type NumberChartConfig,
	type NumberFormat,
} from '../types/chart.types'
import type { Chart } from './chart'
import type { ChartRead } from './chart_view'

// A selected chart's four properties on the shell's selection toolbar: its type,
// how its numbers print, its sort and its color. `read` is the read on screen,
// which knows the columns to sort by; `reading` names the reading a Number tile
// shows, whose color is its own. The chart saves itself on each change.

const FORMATS: { label: string; value: string; format: NumberFormat }[] = [
	{ label: '1,234', value: 'plain', format: {} },
	{ label: '1.2K', value: 'short', format: { shorten: true } },
	{ label: '1,234.00', value: 'decimals', format: { decimals: 2 } },
	{ label: '12%', value: 'percent', format: { suffix: '%' } },
]

const sameFormat = (a: NumberFormat, b: NumberFormat) =>
	JSON.stringify(Object.entries(a).sort()) === JSON.stringify(Object.entries(b).sort())

function numberFormat(chart: Chart): ElementProperty {
	const config = chart.doc.config
	const current = config.number_format || {}
	const preset = FORMATS.find((option) => sameFormat(option.format, current))
	// a format the agent wrote that no preset matches still shows, as itself
	const options = FORMATS.map(({ label, value }) => ({ label, value }))
	if (!preset) options.unshift({ label: __('Custom'), value: 'custom' })
	return {
		name: 'number_format',
		label: __('Number format'),
		icon: 'lucide-hash',
		type: 'select',
		value: preset?.value ?? 'custom',
		options,
		set(value) {
			const picked = FORMATS.find((option) => option.value === value)
			if (!picked) return
			config.number_format = { ...picked.format }
			// the toolbar sets the chart's one format, so no Measure overrides it
			config.number_formats = {}
		},
	}
}

function sort(chart: Chart, read: ChartRead | undefined): ElementProperty {
	const config = chart.doc.config
	const current = config.order_by?.[0]
	const columns = (read?.result.columnOptions || []).map((option) => option.value)
	const named = current?.column.column_name
	if (named && !columns.includes(named)) columns.unshift(named)
	return {
		name: 'sort',
		label: __('Sort'),
		icon: 'lucide-arrow-up-down',
		type: 'select',
		value: current ? `${named}:${current.direction}` : 'none',
		options: [
			{ label: __('Default order'), value: 'none' },
			...columns.flatMap((name) => [
				{ label: `${name} ↑`, value: `${name}:asc` },
				{ label: `${name} ↓`, value: `${name}:desc` },
			]),
		],
		set(value) {
			if (value === 'none') {
				config.order_by = []
				return
			}
			const at = value.lastIndexOf(':')
			config.order_by = [
				{ column: column(value.slice(0, at)), direction: value.slice(at + 1) as 'asc' | 'desc' },
			]
		},
	}
}

// the theme's colors, as a chart with no color of its own draws in
const { tokens } = useChartTokens(ref(document.documentElement))

function color(chart: Chart, reading?: string): ElementProperty | null {
	const type = chart.doc.chart_type
	if (type === 'Number') {
		const config = chart.doc.config as NumberChartConfig
		const columns = config.number_columns || []
		const index = Math.max(reading ? columns.findIndex((c) => c.id === reading) : 0, 0)
		return {
			name: 'color',
			label: __('Color'),
			icon: 'lucide-palette',
			type: 'color',
			value: config.number_column_options?.[index]?.color || 'var(--ink-gray-8)',
			set(value) {
				config.number_column_options ||= []
				const options = (config.number_column_options[index] ||= {})
				options.color = value || undefined
			},
		}
	}
	if (!AXIS_CHARTS.includes(type)) return null
	const series = (chart.doc.config as AxisChartConfig).y_axis?.series
	const first = series?.[0]
	return {
		name: 'color',
		label: __('Color'),
		icon: 'lucide-palette',
		type: 'color',
		value: first?.color?.[0] || paletteColors('sequential', tokens.value, series?.length || 1)[0],
		set(value) {
			if (first) first.color = value ? [value] : undefined
		},
	}
}

export function chartProperties(chart: Chart, read?: ChartRead, reading?: string) {
	const properties: (ElementProperty | null)[] = [
		{
			name: 'chart_type',
			label: __('Type'),
			icon: 'lucide-chart-column',
			type: 'select',
			value: chart.doc.chart_type,
			options: CHARTS.map((type) => ({ label: __(type), value: type })),
			set: (value) => (chart.doc.chart_type = value),
		},
		numberFormat(chart),
		chart.doc.chart_type === 'Number' ? null : sort(chart, read),
		color(chart, reading),
	]
	return properties.filter(Boolean) as ElementProperty[]
}

const TYPE_ICONS: Record<string, string> = {
	Number: 'lucide-hash',
	Bar: 'lucide-chart-column',
	Row: 'lucide-chart-bar',
	Line: 'lucide-chart-line',
	Donut: 'lucide-chart-pie',
	Funnel: 'lucide-filter',
	Table: 'lucide-table',
	Map: 'lucide-map',
}
export const chartIcon = (type: string) => TYPE_ICONS[type] || 'lucide-chart-column'

// what the shell's in-place edit hands back is HTML; a chart title is plain text
export function plainText(html: string) {
	const node = document.createElement('div')
	node.innerHTML = html
	return (node.textContent || '').trim()
}
