<template>
	<form
		class="flex items-end gap-2 rounded-6 border border-outline-gray-2 bg-surface-base py-2 pl-4 pr-2 text-left shadow-sm focus-within:border-outline-gray-3"
		@submit.prevent="emit('submit')"
	>
		<textarea
			v-model="text"
			:rows="rows"
			class="block min-w-0 flex-1 resize-none border-0 bg-transparent px-0 py-1 text-base text-ink-gray-8 placeholder-ink-gray-4 focus:ring-0"
			:placeholder="placeholder"
			@keydown.enter.exact.prevent="emit('submit')"
		/>
		<Button variant="solid" icon="lucide-arrow-up" :disabled="!text.trim()" type="submit" tooltip="Ask" />
	</form>
</template>

<script setup lang="ts">
import { Button } from "frappe-ui"

defineProps<{ rows: number; placeholder: string }>()
const text = defineModel<string>({ required: true })
const emit = defineEmits<{ submit: [] }>()
</script>
