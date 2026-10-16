<template>
	<!-- the grid places the widget; the card inside sizes to what it holds, and the widget spans as many of the grid's 8px rows -->
	<div :class="SPAN[widget.size]" :style="{ gridRowEnd: `span ${rows}` }">
		<section
			ref="card"
			class="flex min-w-0 flex-col overflow-hidden rounded-3 border bg-surface-base"
			:class="editing ? 'border-dashed border-outline-gray-3' : 'border-outline-gray-2'"
		>
			<header class="flex h-9 shrink-0 items-center gap-2 border-b border-outline-gray-1 pl-3 pr-1.5">
				<h2 class="min-w-0 truncate text-sm font-medium text-ink-gray-8">{{ widgetTitle(widget) }}</h2>
				<span v-if="count !== undefined && count !== null" class="text-sm tabular-nums text-ink-gray-5">{{ count }}</span>
				<!-- on a Home, the Space a widget comes from -->
				<RouterLink
					v-if="widget.space_title"
					:to="`/home/s/${encodeURIComponent(widget.space!)}`"
					class="truncate text-xs text-ink-gray-4 hover:text-ink-gray-7"
				>{{ widget.space_title }}</RouterLink>
				<span class="flex-1" />
				<slot v-if="!editing" name="header" />
				<template v-if="editing">
					<Dropdown :options="sizes">
						<Button variant="ghost" size="sm" icon="lucide-scaling" tooltip="Size" />
					</Dropdown>
					<Button variant="ghost" size="sm" icon="lucide-arrow-left" tooltip="Move earlier" :disabled="first" @click="$emit('move', -1)" />
					<Button variant="ghost" size="sm" icon="lucide-arrow-right" tooltip="Move later" :disabled="last" @click="$emit('move', 1)" />
					<Button variant="ghost" size="sm" icon="lucide-x" tooltip="Remove" @click="$emit('remove')" />
				</template>
			</header>
			<div class="flex min-h-0 flex-col" :class="editing ? 'pointer-events-none opacity-60' : ''">
				<slot />
			</div>
		</section>
	</div>
</template>

<script setup lang="ts">
import { useResizeObserver } from "@vueuse/core"
import { Button, Dropdown } from "frappe-ui"
import { computed, ref } from "vue"
import { RouterLink } from "vue-router"

import { type Widget, widgetTitle } from "../home"

const props = defineProps<{ widget: Widget; count?: number | null; editing?: boolean; first?: boolean; last?: boolean }>()
const emit = defineEmits<{ move: [step: number]; remove: []; resize: [size: Widget["size"]] }>()

// a third, two thirds or the whole of the row, so widgets always pack; the whole row on a narrow screen.
// A half (m), from before, is a third
const SPAN: Record<Widget["size"], string> = {
	s: "col-span-12 lg:col-span-4",
	m: "col-span-12 lg:col-span-4",
	l: "col-span-12 lg:col-span-8",
	xl: "col-span-12",
}

// the grid's row track and the gap kept under each card, in px; see WorkspaceGrid
const ROW = 8
const GAP = 12
const card = ref<HTMLElement | null>(null)
const rows = ref(1)
useResizeObserver(card, ([entry]) => {
	rows.value = Math.ceil((entry.target.getBoundingClientRect().height + GAP) / ROW)
})

const sizes = computed(() =>
	(["s", "l", "xl"] as const).map((size) => ({
		label: { s: "A third", l: "Two thirds", xl: "Full width" }[size],
		icon: props.widget.size === size ? "lucide-check" : undefined,
		onClick: () => emit("resize", size),
	}))
)
</script>
