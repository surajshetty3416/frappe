<template>
	<WidgetFrame
		v-bind="$attrs"
		:widget="{ ...widget, title: widget.title || widget.chart_title || null }"
		:studio="widget.chart_editable ? `/studio/analytics/charts/${encodeURIComponent(widget.chart!)}` : undefined"
	>
		<div data-layer="analytics" class="h-[240px] min-h-0 p-2">
			<ChartBodyView v-if="ready" :key="`${widget.chart}/${refreshed}`" :chart="widget.chart!" />
		</div>
	</WidgetFrame>
</template>

<script setup lang="ts">
import { defineAsyncComponent, ref } from "vue"

import { type Widget, refreshed } from "../home"
import WidgetFrame from "./WidgetFrame.vue"

defineOptions({ inheritAttrs: false })
defineProps<{ widget: Widget }>()

const ChartBodyView = defineAsyncComponent(() => import("./ChartBodyView.vue"))

const ready = ref(false)
import("@analytics/session").then(async ({ default: session }) => {
	await session.initialize()
	ready.value = true
})
</script>
