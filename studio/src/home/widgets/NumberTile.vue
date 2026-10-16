<template>
	<!-- a number chart's readings, each a tile as a dashboard cell draws it -->
	<div data-layer="analytics" class="relative min-h-[88px]" :class="editing ? 'opacity-60' : ''">
		<ChartBodyView v-if="ready" :key="`${widget.chart}/${refreshed}`" :chart="widget.chart!" />
		<div v-if="editing" class="absolute right-1.5 top-1.5 flex gap-0.5">
			<Button
				v-if="widget.chart_editable"
				variant="ghost"
				size="sm"
				icon="lucide-pencil"
				tooltip="Edit in Studio"
				:route="`/studio/analytics/charts/${encodeURIComponent(widget.chart!)}`"
			/>
			<Button variant="ghost" size="sm" icon="lucide-x" tooltip="Remove" @click="$emit('remove')" />
		</div>
	</div>
</template>

<script setup lang="ts">
import { Button } from "frappe-ui"
import { defineAsyncComponent, ref } from "vue"

import { type Widget, refreshed } from "../home"

defineProps<{ widget: Widget; editing?: boolean }>()
defineEmits<{ remove: [] }>()

const ChartBodyView = defineAsyncComponent(() => import("./ChartBodyView.vue"))

const ready = ref(false)
import("@analytics/session").then(async ({ default: session }) => {
	await session.initialize()
	ready.value = true
})
</script>
