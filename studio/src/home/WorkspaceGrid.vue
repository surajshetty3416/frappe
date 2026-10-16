<template>
	<div class="flex flex-col gap-3">
		<!-- the numbers the person watches, as one strip of tiles over the work -->
		<div v-if="numbers.length" class="flex flex-wrap gap-3">
			<NumberTile
				v-for="widget in numbers"
				:key="widget.id"
				:widget="widget"
				:editing="editing"
				@remove="remove(widget)"
			/>
		</div>
		<div class="grid grid-flow-row-dense auto-rows-[8px] grid-cols-12 gap-x-3">
			<component
				:is="WIDGETS[widget.type]"
				v-for="widget in rest"
				:key="widget.id"
				:widget="widget"
				:editing="editing"
				:first="widget === rest[0]"
				:last="widget === rest[rest.length - 1]"
				@move="(step: number) => move(widget, step)"
				@remove="remove(widget)"
				@resize="(size: Widget['size']) => resize(widget, size)"
			/>
		</div>
	</div>
</template>

<script setup lang="ts">
import { type Component, computed } from "vue"

import type { Widget } from "./home"
import ChartWidget from "./widgets/ChartWidget.vue"
import EmbedWidget from "./widgets/EmbedWidget.vue"
import InboxWidget from "./widgets/InboxWidget.vue"
import NoteWidget from "./widgets/NoteWidget.vue"
import NumberTile from "./widgets/NumberTile.vue"
import QueueWidget from "./widgets/QueueWidget.vue"
import QuickEntryWidget from "./widgets/QuickEntryWidget.vue"

const WIDGETS: Record<Widget["type"], Component> = {
	queue: QueueWidget,
	inbox: InboxWidget,
	chart: ChartWidget,
	quick_entry: QuickEntryWidget,
	embed: EmbedWidget,
	note: NoteWidget,
}

const props = defineProps<{ widgets: Widget[]; editing?: boolean }>()
const emit = defineEmits<{ update: [widgets: Widget[]] }>()

const isNumber = (widget: Widget) => widget.type === "chart" && widget.chart_type === "Number"
const numbers = computed(() => props.widgets.filter(isNumber))
const rest = computed(() => props.widgets.filter((widget) => !isNumber(widget)))

// a move steps past the next widget of the grid, so the numbers strip keeps its own order
function move(widget: Widget, step: number) {
	const next = rest.value[rest.value.indexOf(widget) + step]
	if (!next) return
	const widgets = props.widgets.filter((each) => each !== widget)
	widgets.splice(widgets.indexOf(next) + (step > 0 ? 1 : 0), 0, widget)
	emit("update", widgets)
}

const remove = (widget: Widget) => emit("update", props.widgets.filter((each) => each !== widget))
const resize = (widget: Widget, size: Widget["size"]) =>
	emit("update", props.widgets.map((each) => (each === widget ? { ...each, size } : each)))
</script>
