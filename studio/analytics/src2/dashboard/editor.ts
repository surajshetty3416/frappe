// Insights Dashboard v3 in Studio's editor shell: the always-editable grid as the
// preview, and the shell's contract answered from the dashboard store.
import { defineArtifactEditor, type ElementAction, type ElementProperty } from '@shell/editor'
import { type UseRefHistoryReturn, useDebouncedRefHistory } from '@vueuse/core'
import { call } from 'frappe-ui'
import { type Component, computed, defineComponent, h, ref, shallowReactive, watch } from 'vue'
import { titleNode } from '../charts/editor'
import { chartIcon, chartProperties, plainText } from '../charts/properties'
import JsonCode from '../components/JsonCode.vue'
import { getUniqueId, waitUntil } from '../helpers'
import dayjs from '../helpers/dayjs'
import { __ } from '../translation'
import type { WorkbookDashboardFilter, WorkbookDashboardItem } from '../types/workbook.types'
import useDashboard, { type Dashboard } from './dashboard'
import DashboardDetails from './DashboardDetails.vue'
import DashboardPreview from './DashboardPreview.vue'
import DashboardShareDialog from './DashboardShareDialog.vue'
import FilterProperties from './FilterProperties.vue'
import { BASE_BREAKPOINT, placementsFor, resolveLayouts } from './grid_placement'

const current = ref('')
const dashboard = computed(() => (current.value ? useDashboard(current.value) : null))
const sharing = ref(false)
const views = ref<number>()

let host: HTMLElement | null = null
const tileNode = (id: string) =>
	host?.querySelector<HTMLElement>(`[data-tile="${CSS.escape(id)}"]`) ?? null
const tileIndex = (id: string) =>
	dashboard.value?.doc.items.findIndex((item) => item.layout.i === id) ?? -1
const tile = (id: string) => dashboard.value?.doc.items[tileIndex(id)] as WorkbookDashboardItem | undefined

function countViews(name: string) {
	views.value = undefined
	call('frappe.client.get_count', {
		doctype: 'View Log',
		filters: { reference_doctype: 'Insights Dashboard v3', reference_name: name },
	}).then((count) => current.value === name && (views.value = count as number))
}

// Undo and redo walk the tiles a person changed here. Made once the dashboard loads, so
// the load is not a step, and cleared when someone else's save replaces the tiles.
const histories = shallowReactive(new Map<string, UseRefHistoryReturn<unknown, unknown>>())
const history = computed(() => histories.get(current.value))
async function track(name: string, store: Dashboard) {
	if (histories.has(name)) return
	await waitUntil(() => Boolean(store.isloaded))
	if (histories.has(name)) return
	const items = computed({
		get: () => store.doc.items,
		set: (value) => (store.doc.items = value),
	})
	histories.set(name, useDebouncedRefHistory(items, { deep: true, clone: true, debounce: 300 }) as any)
}

function duplicateTile(store: Dashboard, index: number) {
	const item = store.doc.items[index]
	const copy = JSON.parse(JSON.stringify(item)) as WorkbookDashboardItem
	// below the original; the grid makes room for it
	copy.layout = { ...item.layout, i: getUniqueId(), y: item.layout.y + item.layout.h }
	delete copy.layouts
	if (copy.type === 'filter') {
		const names = new Set(store.doc.items.map((other) => (other.type === 'filter' ? other.filter_name : '')))
		let n = 2
		while (names.has(`${copy.filter_name} ${n}`)) n++
		copy.filter_name = `${copy.filter_name} ${n}`
	}
	store.doc.items.splice(index + 1, 0, copy)
}

const DashboardArtifactPreview = defineComponent({
	name: 'DashboardArtifactPreview',
	props: { name: { type: String, required: true } },
	setup(props) {
		const root = ref<HTMLElement | null>(null)
		watch(root, (value) => (host = value))
		watch(
			() => props.name,
			(name) => {
				current.value = name
				sharing.value = false
				countViews(name)
			},
			{ immediate: true },
		)
		watch(dashboard, (store) => store && track(props.name, store), { immediate: true })
		return () =>
			// the same sheet on the same surface as a Builder page's preview
			h('div', { ref: root, class: 'h-full w-full bg-surface-gray-2 p-6' }, [
				h('div', { class: 'h-full w-full overflow-hidden rounded-[2px] bg-surface-base shadow-[0_0_0_1px_var(--outline-gray-2)]' }, [h(DashboardPreview, { key: props.name, name: props.name })]),
				sharing.value
					? h(DashboardShareDialog as Component, {
							name: props.name,
							modelValue: sharing.value,
							'onUpdate:modelValue': (open: boolean) => (sharing.value = open),
						})
					: null,
			])
	},
})

function filterProperties(index: number, filter: WorkbookDashboardFilter): ElementProperty[] {
	return [
		{
			name: 'filter',
			label: __('Filter'),
			icon: 'lucide-list-filter',
			type: 'popover',
			value: __(filter.filter_type),
			component: { component: FilterProperties, props: { name: current.value, index } },
			set: () => {},
		},
	]
}

export default defineArtifactEditor({
	preview: DashboardArtifactPreview,

	title: () => dashboard.value?.doc.title || __('Untitled dashboard'),
	rename(title) {
		if (!dashboard.value) return Promise.resolve()
		dashboard.value.doc.title = title
		return dashboard.value.save()
	},
	status() {
		const store = dashboard.value
		if (store?.saving || store?.isdirty) return { label: __('Saving…'), theme: 'gray' }
		if (store?.doc.visibility === 'Public') return { label: __('Public'), theme: 'green' }
		return { label: __('Private'), theme: 'gray' }
	},
	primaryAction() {
		const store = dashboard.value
		if (!store?.doc.can_share) return null
		return {
			label: __('Share'),
			run: async () => (sharing.value = true),
		}
	},
	details() {
		const store = dashboard.value
		if (!store) return []
		const times = store
			.linkedCharts()
			.map((chart) => store.chartView(chart).executedAt?.getTime())
			.filter(Boolean) as number[]
		return [
			{ label: __('Views'), value: views.value === undefined ? '—' : String(views.value) },
			{ label: __('Last refreshed'), value: times.length ? dayjs(Math.max(...times)).fromNow() : '—' },
		]
	},
	code: () => ({ language: 'json', content: JSON.stringify(dashboard.value?.doc.items ?? [], null, 2) }),
	detailsForm: () => (current.value ? { component: DashboardDetails, props: { name: current.value } } : null),
	codeTabs() {
		const store = dashboard.value
		if (!store) return []
		return [
			{
				name: 'tiles',
				label: __('Tiles'),
				component: {
					component: JsonCode,
					props: { read: () => store.doc.items, write: (items: WorkbookDashboardItem[]) => (store.doc.items = items) },
				},
			},
		]
	},
	async reload(modified) {
		const store = dashboard.value
		if (!store) return
		if (store.saving) await waitUntil(() => !store.saving)
		// the save this tab made itself
		if (modified && modified === (store.doc as { modified?: string }).modified) return
		await store.load()
		store.refresh(true)
		history.value?.clear()
	},
	undo: () => history.value?.undo(),
	redo: () => history.value?.redo(),

	select(id) {
		const store = dashboard.value
		if (!store) return
		const index = id ? tileIndex(id) : -1
		store.selectedIndex = index === -1 ? undefined : index
	},
	actions(id): ElementAction[] {
		const store = dashboard.value
		if (!store || tileIndex(id) === -1) return []
		return [
			{ name: 'duplicate', label: __('Duplicate'), icon: 'lucide-copy', run: () => duplicateTile(store, tileIndex(id)) },
			{ name: 'delete', label: __('Delete'), icon: 'lucide-trash-2', run: () => store.removeItem(tileIndex(id)) },
		]
	},
	resizable: (id) => Boolean(tile(id)),
	resize(id, size) {
		const store = dashboard.value
		const cell = tileNode(id)?.parentElement
		if (!store || !cell) return
		const key = BASE_BREAKPOINT.key
		const rules = store.cellRules
		const verticalCompact = Boolean(store.doc.vertical_compact_layout)
		const from = resolveLayouts(placementsFor(store.doc.items, key, rules), { verticalCompact, rules })
		const now = from.find((layout) => layout.i === id)
		if (!now) return
		// the tile sits inside its cell's padding
		const { width, height } = cell.getBoundingClientRect()
		const padding = width - (tileNode(id)?.offsetWidth ?? width)
		const w = Math.min(Math.max(Math.round(((size.width + padding) / width) * now.w), 1), BASE_BREAKPOINT.columns - now.x)
		const h = rules[id]?.height ?? Math.max(Math.round(((size.height + padding) / height) * now.h), 1)
		const asked = from.map((layout) => (layout.i === id ? { ...layout, w, h } : layout))
		store.moveItems(key, resolveLayouts(asked, { pinned: id, verticalCompact, rules }), from, verticalCompact)
	},

	elementAt(node) {
		const element = node.closest<HTMLElement>('[data-tile]')
		if (!element || !host?.contains(element)) return null
		const id = element.dataset.tile as string
		const item = tile(id)
		if (!item) return null
		if (item.type === 'chart') {
			const chart = dashboard.value?.chartsByName[item.chart]
			return {
				id,
				label: chart?.doc.title || __('Chart'),
				icon: chartIcon(chart?.doc.chart_type || ''),
				hasText: chart?.doc.chart_type !== 'Number',
			}
		}
		if (item.type === 'filter') {
			return { id, label: item.filter_name, icon: 'lucide-list-filter', hasText: false }
		}
		return { id, label: __('Text'), icon: 'lucide-type', hasText: true }
	},
	elementRect: (id) => tileNode(id)?.getBoundingClientRect() ?? null,
	textNode(id) {
		const node = tileNode(id)
		if (tile(id)?.type === 'text') return node?.querySelector<HTMLElement>('[data-text]') ?? null
		return titleNode(node)
	},
	setText(id, html) {
		const item = tile(id)
		if (item?.type === 'text') {
			item.text = html
			return
		}
		const title = plainText(html)
		const chart = item?.type === 'chart' ? dashboard.value?.chartsByName[item.chart] : undefined
		if (chart && title) chart.doc.title = title
	},
	properties(id) {
		const item = tile(id)
		const store = dashboard.value
		if (!item || !store) return []
		if (item.type === 'filter') return filterProperties(tileIndex(id), item)
		if (item.type !== 'chart') return []
		const chart = store.chartsByName[item.chart]
		return chart ? chartProperties(chart, store.chartView(item.chart), item.reading) : []
	},
})
