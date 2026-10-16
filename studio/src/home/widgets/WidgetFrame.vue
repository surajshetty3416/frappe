<template>
	<section
		class="flex min-w-0 flex-col overflow-hidden rounded-8 border bg-surface-base"
		:class="[SPAN[widget.size], editing ? 'border-dashed border-outline-gray-3' : 'border-outline-gray-2']"
	>
		<header class="flex h-11 shrink-0 items-center gap-2 border-b border-outline-gray-1 px-3">
			<h2 class="min-w-0 truncate text-base font-medium text-ink-gray-8">{{ widgetTitle(widget) }}</h2>
			<span v-if="count !== undefined && count !== null" class="rounded-full bg-surface-gray-2 px-1.5 text-xs font-medium text-ink-gray-6">
				{{ count }}
			</span>
			<span class="flex-1" />
			<slot name="header" />
			<template v-if="editing">
				<Dropdown :options="sizes">
					<Button variant="ghost" size="sm" icon="lucide-scaling" tooltip="Size" />
				</Dropdown>
				<Button variant="ghost" size="sm" icon="lucide-arrow-left" tooltip="Move earlier" :disabled="first" @click="$emit('move', -1)" />
				<Button variant="ghost" size="sm" icon="lucide-arrow-right" tooltip="Move later" :disabled="last" @click="$emit('move', 1)" />
				<Button variant="ghost" size="sm" icon="lucide-trash-2" tooltip="Remove" @click="$emit('remove')" />
			</template>
		</header>
		<div class="flex min-h-0 flex-1 flex-col" :class="editing ? 'pointer-events-none opacity-70' : ''">
			<slot />
		</div>
	</section>
</template>

<script setup lang="ts">
import { Button, Dropdown } from "frappe-ui"
import { computed } from "vue"

import { type Widget, widgetTitle } from "../home"

const props = defineProps<{ widget: Widget; count?: number | null; editing?: boolean; first?: boolean; last?: boolean }>()
const emit = defineEmits<{ move: [step: number]; remove: []; resize: [size: Widget["size"]] }>()

// a third, half, two thirds or the whole of the row; one column on a narrow screen
const SPAN: Record<Widget["size"], string> = {
	s: "col-span-6 lg:col-span-2",
	m: "col-span-6 lg:col-span-3",
	l: "col-span-6 lg:col-span-4",
	xl: "col-span-6",
}

const sizes = computed(() =>
	(["s", "m", "l", "xl"] as const).map((size) => ({
		label: { s: "Small", m: "Medium", l: "Large", xl: "Full width" }[size],
		icon: props.widget.size === size ? "lucide-check" : undefined,
		onClick: () => emit("resize", size),
	}))
)
</script>
