<script setup lang="ts">
import { Button, call } from 'frappe-ui'
import { computed, ref, watch } from 'vue'
import { waitUntil } from '../helpers'
import dayjs from '../helpers/dayjs'
import { __ } from '../translation'
import useDashboard from './dashboard'

// The dashboard's Details drawer: who owns it, how often it is opened, and when
// its tiles last fetched.
const props = defineProps<{ name: string }>()

const dashboard = useDashboard(props.name)

const views = ref<number>()
watch(
	() => dashboard.doc.name,
	(name) => {
		if (!name) return
		call('frappe.client.get_count', {
			doctype: 'View Log',
			filters: { reference_doctype: 'Insights Dashboard v3', reference_name: name },
		}).then((count) => (views.value = count as number))
	},
	{ immediate: true },
)

// mounted on its own, the drawer still shows when the tiles last fetched
waitUntil(() => dashboard.isloaded).then(() => dashboard.refresh())
const reads = computed(() => dashboard.linkedCharts().map((chart) => dashboard.chartView(chart)))
const refreshing = computed(() => reads.value.some((read) => read.executing))
const lastRefreshed = computed(() => {
	const times = reads.value.map((read) => read.executedAt?.getTime()).filter(Boolean) as number[]
	return times.length ? dayjs(Math.max(...times)).fromNow() : undefined
})

const rows = computed(() => [
	{ label: __('Owner'), value: dashboard.doc.owner },
	{ label: __('Views'), value: views.value ?? '—' },
	{ label: __('Last refreshed'), value: lastRefreshed.value ?? '—' },
])
</script>

<template>
	<div class="flex flex-col gap-3">
		<div v-for="row in rows" :key="row.label" class="flex items-center justify-between gap-2">
			<span class="text-p-sm text-ink-gray-5">{{ row.label }}</span>
			<span class="truncate text-p-sm text-ink-gray-8">{{ row.value }}</span>
		</div>
		<Button
			:label="__('Refresh all tiles')"
			icon-left="lucide-refresh-cw"
			:loading="refreshing"
			@click="dashboard.refresh(true)"
		/>
	</div>
</template>
