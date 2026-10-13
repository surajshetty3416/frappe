<template>
	<span
		v-if="chip.badge"
		class="grid size-4 flex-none place-items-center rounded-full bg-surface-blue-6 text-2xs font-medium text-ink-base ring-2 ring-surface-base"
		>{{ chip.badge }}</span
	>
	<span v-else :class="chip.icon" class="size-4 flex-none text-ink-gray-5" />
</template>

<script setup>
// a chip's lead: a comment's pin number, or an icon
defineProps({ chip: { type: Object, required: true } })
</script>
