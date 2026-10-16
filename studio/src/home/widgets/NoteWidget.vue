<template>
	<WidgetFrame v-bind="$attrs" :widget="widget">
		<p class="whitespace-pre-wrap px-3 py-2.5 text-sm leading-relaxed text-ink-gray-7">{{ widget.text }}</p>
	</WidgetFrame>
</template>

<script setup lang="ts">
import type { Widget } from "../home"
import WidgetFrame from "./WidgetFrame.vue"

defineOptions({ inheritAttrs: false })
defineProps<{ widget: Widget }>()
</script>
