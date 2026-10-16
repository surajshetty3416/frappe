<template>
	<!-- a desk Number Card in the strip of numbers -->
	<div
		class="relative flex h-[88px] w-[240px] flex-col justify-between rounded-3 border border-outline-gray-2 bg-surface-base px-4 py-3"
		:class="editing ? 'opacity-60' : ''"
	>
		<p class="truncate text-sm text-ink-gray-5">{{ widget.title || data?.label }}</p>
		<p v-if="data" class="truncate text-2xl font-semibold tabular-nums tracking-tight text-ink-gray-9">{{ value }}</p>
		<Skeleton v-else class="h-6 w-20 rounded" />
		<Button v-if="editing" class="absolute right-1.5 top-1.5" variant="ghost" size="sm" icon="lucide-x" tooltip="Remove" @click="$emit('remove')" />
	</div>
</template>

<script setup lang="ts">
import { Button, Skeleton } from "frappe-ui"
import { computed, ref, watch } from "vue"

import { type Widget, getWidget, refreshed } from "../home"

const props = defineProps<{ widget: Widget; editing?: boolean }>()
defineEmits<{ remove: [] }>()

const data = ref<{ label: string; value: number | null; currency: string | null } | null>(null)
watch(
	() => [props.widget.id, refreshed.value],
	async () => (data.value = await getWidget<NonNullable<typeof data.value>>(props.widget).catch(() => ({ label: "", value: null, currency: null }))),
	{ immediate: true }
)

const value = computed(() => {
	const number = data.value?.value
	if (number === null || number === undefined) return "—"
	const compact = new Intl.NumberFormat(undefined, { notation: "compact", maximumFractionDigits: 1 }).format(number)
	return data.value?.currency ? `${data.value.currency} ${compact}` : compact
})
</script>
