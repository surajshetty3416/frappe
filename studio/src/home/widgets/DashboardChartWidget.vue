<template>
	<WidgetFrame v-bind="$attrs" :widget="{ ...widget, title: widget.title || data?.label || null }">
		<div v-if="!data" class="flex flex-col gap-2 p-3">
			<Skeleton v-for="i in 4" :key="i" class="h-4 w-full rounded" />
		</div>
		<p v-else-if="!points.length" class="px-3 py-2.5 text-sm text-ink-gray-5">No data yet.</p>
		<!-- a series over time as an area, categories as horizontal bars -->
		<svg v-else-if="overTime" class="h-[200px] w-full p-3" :viewBox="`0 0 ${W} ${H}`" preserveAspectRatio="none" role="img" :aria-label="data.label">
			<defs>
				<linearGradient :id="`fill-${uid}`" x1="0" x2="0" y1="0" y2="1">
					<stop offset="0%" stop-color="currentColor" stop-opacity="0.15" />
					<stop offset="100%" stop-color="currentColor" stop-opacity="0" />
				</linearGradient>
			</defs>
			<g class="text-ink-gray-7">
				<path :d="`${line} L ${W} ${H} L 0 ${H} Z`" :fill="`url(#fill-${uid})`" />
				<path :d="line" fill="none" stroke="currentColor" stroke-width="1.5" vector-effect="non-scaling-stroke" />
			</g>
		</svg>
		<ul v-else class="flex flex-col gap-1.5 p-3">
			<li v-for="point in points.slice(0, 8)" :key="point.label" class="grid grid-cols-[minmax(0,8rem)_1fr_auto] items-center gap-2 text-sm">
				<span class="truncate text-ink-gray-6">{{ point.label }}</span>
				<span class="h-2 rounded-full bg-surface-gray-7" :style="{ width: `${Math.max(2, (point.value / max) * 100)}%` }" />
				<span class="tabular-nums text-ink-gray-7">{{ point.value.toLocaleString() }}</span>
			</li>
		</ul>
		<p v-if="overTime && points.length" class="flex justify-between px-3 pb-2 text-xs tabular-nums text-ink-gray-4">
			<span>{{ points[0].label }}</span><span>{{ points[points.length - 1].label }}</span>
		</p>
	</WidgetFrame>
</template>

<script setup lang="ts">
import { Skeleton } from "frappe-ui"
import { computed, ref, useId, watch } from "vue"

import { type Widget, getWidget, refreshed } from "../home"
import WidgetFrame from "./WidgetFrame.vue"

defineOptions({ inheritAttrs: false })
const props = defineProps<{ widget: Widget }>()
const uid = useId()

const W = 400
const H = 160

const data = ref<{ label: string; type: string; labels: string[]; datasets: { name?: string; values: number[] }[] } | null>(null)
watch(
	() => [props.widget.id, refreshed.value],
	async () => (data.value = await getWidget<NonNullable<typeof data.value>>(props.widget).catch(() => ({ label: "", type: "", labels: [], datasets: [] }))),
	{ immediate: true }
)

// the first series against its labels
const points = computed(() =>
	(data.value?.labels ?? []).map((label, i) => ({ label: String(label), value: Number(data.value?.datasets[0]?.values[i] ?? 0) }))
)
const max = computed(() => Math.max(1, ...points.value.map((point) => point.value)))
const overTime = computed(() => ["Line", "Bar"].includes(data.value?.type ?? "") && points.value.length > 8)
const line = computed(() =>
	points.value
		.map((point, i) => `${i ? "L" : "M"} ${(i / Math.max(1, points.value.length - 1)) * W} ${H - (point.value / max.value) * (H - 8)}`)
		.join(" ")
)
</script>
