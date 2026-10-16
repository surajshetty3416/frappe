<template>
	<WidgetFrame v-bind="$attrs" :widget="{ ...widget, title: widget.title || title }">
		<div data-layer="analytics" class="h-[240px] min-h-0 p-2">
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
call("frappe.client.get_value", { doctype: "Insights Chart v3", filters: props.widget.chart, fieldname: "title" })
	.then((doc) => (title.value = doc?.title ?? ""))
	.catch(() => {})
</script>
