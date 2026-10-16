<template>
	<!-- a number chart's readings, each a tile as a dashboard cell draws it -->
	<div data-layer="analytics" class="relative h-[88px]" :class="editing ? 'opacity-60' : ''">
		<ChartBodyView v-if="ready" :key="`${widget.chart}/${refreshed}`" :chart="widget.chart!" />
		<Button
			v-if="editing"
			class="absolute right-1.5 top-1.5"
			variant="ghost"
			size="sm"
			icon="lucide-x"
			tooltip="Remove"
			@click="$emit('remove')"
		/>
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
