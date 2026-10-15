<template>
	<div class="flex flex-col items-start gap-1 px-2 py-6">
		<p class="text-base font-medium text-ink-gray-8">{{ title }}</p>
		<p class="max-w-[520px] text-p-sm text-ink-gray-5">{{ text }}</p>
		<div v-if="$slots.default" class="mt-3 flex flex-wrap gap-2"><slot /></div>
	</div>
</template>

<script setup lang="ts">
defineProps<{ title: string; text: string }>()
</script>
