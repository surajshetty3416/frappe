<template>
	<div class="grid grid-flow-row-dense grid-cols-6 items-start gap-4">
		<component
			:is="WIDGETS[widget.type]"
			v-for="(widget, i) in widgets"
			:key="widget.id"
			:widget="widget"
			:editing="editing"
			:first="i === 0"
			:last="i === widgets.length - 1"
			@move="(step: number) => move(i, step)"
			@remove="remove(i)"
			@resize="(size: Widget['size']) => resize(i, size)"
		/>
	</div>
</template>

<script setup lang="ts">
import type { Component } from "vue"

import type { Widget } from "./home"
import ChartWidget from "./widgets/ChartWidget.vue"
import EmbedWidget from "./widgets/EmbedWidget.vue"
import InboxWidget from "./widgets/InboxWidget.vue"
import NoteWidget from "./widgets/NoteWidget.vue"
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

function move(i: number, step: number) {
	const widgets = [...props.widgets]
	const [widget] = widgets.splice(i, 1)
	widgets.splice(i + step, 0, widget)
	emit("update", widgets)
}

const remove = (i: number) => emit("update", props.widgets.filter((_, at) => at !== i))
const resize = (i: number, size: Widget["size"]) =>
	emit("update", props.widgets.map((widget, at) => (at === i ? { ...widget, size } : widget)))
</script>
