<template>
	<WidgetFrame v-bind="$attrs" :widget="{ ...widget, title: widget.title || title }">
		<div data-layer="analytics" class="min-h-0 p-2" :class="number ? 'h-[150px]' : 'h-[300px]'">
			<ChartBodyView v-if="ready" :key="`${widget.chart}/${refreshed}`" :chart="widget.chart!" />
		</div>
	</WidgetFrame>
</template>

<script setup lang="ts">
import { call } from "frappe-ui"
import { defineAsyncComponent, ref } from "vue"

import { type Widget, refreshed } from "../home"
import WidgetFrame from "./WidgetFrame.vue"

defineOptions({ inheritAttrs: false })
const props = defineProps<{ widget: Widget }>()

const ChartBodyView = defineAsyncComponent(() => import("./ChartBodyView.vue"))

const ready = ref(false)
import("@analytics/session").then(async ({ default: session }) => {
	await session.initialize()
	ready.value = true
})

const title = ref("")
const number = ref(false)
call("frappe.client.get_value", { doctype: "Insights Chart v3", filters: props.widget.chart, fieldname: ["title", "chart_type"] })
	.then((doc) => {
		title.value = doc?.title ?? ""
		number.value = doc?.chart_type === "Number"
	})
	.catch(() => {})
</script>
