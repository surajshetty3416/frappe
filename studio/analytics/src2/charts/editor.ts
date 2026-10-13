// Insights Chart v3 in Studio's editor shell: the chart with its rows as the
// preview, and the shell's contract answered from the chart store.
import { defineArtifactEditor } from '@shell/editor'
import { computed, defineComponent, h, ref, shallowRef, watch } from 'vue'
import { waitUntil } from '../helpers'
import dayjs from '../helpers/dayjs'
import useQuery, { type Query } from '../query/query'
import { __ } from '../translation'
import useChart from './chart'
import useChartPreview from './chart_preview'
import ChartPreview from './ChartPreview.vue'
import { chartIcon, chartProperties, plainText } from './properties'

const current = ref('')
const chart = computed(() => (current.value ? useChart(current.value) : null))
const read = computed(() => (chart.value ? useChartPreview(chart.value) : undefined))

// The query behind the chart, resolved once it loads. A store registers itself
// when it is made, so it is resolved here and not in a computed.
const query = shallowRef<Query>()
async function resolveQuery(name: string) {
	query.value = undefined
	const owner = useChart(name)
	await waitUntil(() => !owner.pending && Boolean(owner.doc.query))
	if (current.value !== name) return
	const q = useQuery(owner.doc.query)
	await waitUntil(() => !q.pending)
	if (!q.doc.is_script_query && !q.doc.is_native_query) q.ensureResult()
	if (current.value === name) query.value = q
}

let host: HTMLElement | null = null
const chartNode = () => host?.querySelector<HTMLElement>('[data-tile="chart"]') ?? null

const ChartArtifactPreview = defineComponent({
	name: 'ChartArtifactPreview',
	props: { name: { type: String, required: true } },
	setup(props) {
		const root = ref<HTMLElement | null>(null)
		watch(root, (value) => (host = value))
		watch(
			() => props.name,
			(name) => {
				current.value = name
				resolveQuery(name)
			},
			{ immediate: true },
		)
		return () =>
			// the same sheet on the same surface as a Builder page's preview
			h('div', { ref: root, class: 'h-full w-full bg-surface-gray-2 p-6' }, [
				h('div', { class: 'h-full w-full overflow-hidden rounded-[2px] bg-surface-base shadow-[0_0_0_1px_var(--outline-gray-2)]' }, [h(ChartPreview, { key: props.name, name: props.name })]),
			])
	},
})

function source(q?: Query) {
	const first = q?.doc.operations?.[0] as any
	if (first?.type === 'source') {
		return first.table.type === 'query' ? first.table.query_name : first.table.table_name
	}
	if (first?.type === 'sql') return first.data_source
	if (first?.type === 'code') return __('Python script')
}

export default defineArtifactEditor({
	preview: ChartArtifactPreview,

	title: () => chart.value?.doc.title || __('Untitled chart'),
	rename(title) {
		if (!chart.value) return Promise.resolve()
		chart.value.doc.title = title
		return chart.value.save()
	},
	status() {
		if (chart.value?.saving || chart.value?.isdirty) return { label: __('Saving…'), theme: 'gray' }
		return { label: __('Saved'), theme: 'gray' }
	},
	primaryAction: () => null,
	details() {
		const executedAt = read.value?.executedAt
		const rows = [
			{ label: __('Query'), value: query.value?.doc.title || chart.value?.doc.query || '—' },
			{ label: __('Source'), value: source(query.value) || '—' },
			{ label: __('Last fetched'), value: executedAt ? dayjs(executedAt).fromNow() : '—' },
		]
		if (chart.value?.doc.description) {
			rows.push({ label: __('Description'), value: chart.value.doc.description })
		}
		return rows
	},
	code() {
		const q = query.value
		if (!q) return { language: 'sql', content: '' }
		if (q.doc.is_script_query) return { language: 'python', content: q.getCodeOperation()?.code || '' }
		if (q.doc.is_native_query) return { language: 'sql', content: (q.getSQLOperation() as any)?.raw_sql || '' }
		return { language: 'sql', content: q.result.executedSQL || '' }
	},
	async reload(modified) {
		const store = chart.value
		if (!store) return
		if (store.saving) await waitUntil(() => !store.saving)
		// the save this tab made itself
		if (modified && modified === (store.doc as { modified?: string }).modified) return
		await store.load()
		read.value?.load(true)
	},

	elementAt(node) {
		const element = node.closest<HTMLElement>('[data-tile="chart"]')
		if (!element || !host?.contains(element) || !chart.value) return null
		return {
			id: 'chart',
			label: chart.value.doc.title || __('Chart'),
			icon: chartIcon(chart.value.doc.chart_type),
			hasText: chart.value.doc.chart_type !== 'Number',
		}
	},
	elementRect: () => chartNode()?.getBoundingClientRect() ?? null,
	textNode: () => titleNode(chartNode()),
	setText(_, html) {
		const title = plainText(html)
		if (chart.value && title) chart.value.doc.title = title
	},
	properties: () => (chart.value ? chartProperties(chart.value, read.value) : []),
})

// the chart title frappe-ui's chart card prints. A number card titles each
// reading with its Measure instead, so it has no chart title to edit.
export function titleNode(card: HTMLElement | null) {
	return card?.querySelector<HTMLElement>('[data-slot="chart-header"] span.min-w-0.truncate') ?? null
}
