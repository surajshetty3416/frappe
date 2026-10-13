// Insights Dashboard v3 in Studio's editor shell: the always-editable grid as the
// preview, and the shell's contract answered from the dashboard store.
import { defineArtifactEditor, type ElementProperty } from '@shell/editor'
import { call } from 'frappe-ui'
import { type Component, computed, defineComponent, h, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { titleNode } from '../charts/editor'
import { chartIcon, chartProperties, plainText } from '../charts/properties'
import { waitUntil } from '../helpers'
import dayjs from '../helpers/dayjs'
import { __ } from '../translation'
import type { WorkbookDashboardFilter, WorkbookDashboardItem } from '../types/workbook.types'
import useDashboard from './dashboard'
import DashboardPreview from './DashboardPreview.vue'
import DashboardShareDialog from './DashboardShareDialog.vue'

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

// Delete or Backspace removes the selected tile, unless the key is typing somewhere
function onKeydown(event: KeyboardEvent) {
	if (event.key !== 'Delete' && event.key !== 'Backspace') return
	const target = event.target as HTMLElement | null
	if (target?.closest('input, textarea, select, [contenteditable="true"]')) return
	const store = dashboard.value
	// the shell's toolbar shows while a tile is selected; Esc clears the shell's selection, not the store's
	if (store?.selectedIndex === undefined || !host?.isConnected || !document.querySelector('[data-selection-ui]')) return
	event.preventDefault()
	store.removeItem(store.selectedIndex)
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
		onMounted(() => window.addEventListener('keydown', onKeydown))
		onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
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

function filterProperties(filter: WorkbookDashboardFilter): ElementProperty[] {
	return [
		{
			name: 'filter_type',
			label: __('Type'),
			icon: 'lucide-list-filter',
			type: 'select',
			value: filter.filter_type,
			options: ['String', 'Number', 'Date'].map((type) => ({ label: __(type), value: type })),
			set(value) {
				filter.filter_type = value as WorkbookDashboardFilter['filter_type']
				// the default and the linked columns were for the other type
				filter.default_operator = undefined
				filter.default_value = undefined
				filter.links = {}
			},
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
	code: () => ({
		language: 'json',
		content: JSON.stringify(dashboard.value?.doc.items ?? [], null, 2),
	}),
	async reload(modified) {
		const store = dashboard.value
		if (!store) return
		if (store.saving) await waitUntil(() => !store.saving)
		// the save this tab made itself
		if (modified && modified === (store.doc as { modified?: string }).modified) return
		await store.load()
		store.refresh(true)
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
		if (item.type === 'filter') return filterProperties(item)
		if (item.type !== 'chart') return []
		const chart = store.chartsByName[item.chart]
		return chart ? chartProperties(chart, store.chartView(item.chart), item.reading) : []
	},
})
