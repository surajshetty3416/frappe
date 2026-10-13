<template>
	<button
		type="button"
		class="-mx-1.5 flex w-fit select-none items-center gap-1.5 rounded-4 px-1.5 py-1 text-sm text-ink-gray-5 transition-colors duration-150 ease-out hover:text-ink-gray-7"
		:aria-expanded="expanded"
		@click="$emit('toggle')"
	>
		<span>{{ label }}</span>
		<span class="lucide-chevron-right size-3.5 flex-none transition-transform" :class="expanded ? 'rotate-90' : ''" />
	</button>
</template>

<script setup>
defineProps({
	label: { type: String, required: true },
	expanded: { type: Boolean, default: false },
})

defineEmits(["toggle"])
</script>
