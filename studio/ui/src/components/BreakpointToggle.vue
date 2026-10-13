<template>
	<TabButtons
		v-if="canvas"
		:options="canvas.canvasProps.breakpoints.map((breakpoint) => ({ value: breakpoint.device, icon: breakpoint.icon, label: '', title: breakpoint.displayName }))"
		:modelValue="active"
		@update:modelValue="(device) => canvas?.setBreakpoint(device as BreakpointConfig['device'])"
	/>
</template>

<script setup lang="ts">
import { computed } from "vue"
import { TabButtons } from "frappe-ui"
import useCanvasStore from "@ui/stores/canvasStore"
import type { BreakpointConfig } from "@ui/types/StudioCanvas"

const canvasStore = useCanvasStore()
const canvas = computed(() => canvasStore.activeCanvas)
const active = computed(() => canvas.value?.canvasProps.breakpoints.find((breakpoint) => breakpoint.visible)?.device)
</script>
