<script setup lang="ts">
import { Button, toast } from 'frappe-ui'
import { ref, watch } from 'vue'
import { __ } from '../translation'
import Code from './Code.vue'

// A part of an artifact as JSON in the shell's Code drawer. Cmd+Enter or Apply writes it
// back, and the artifact saves itself.
const props = defineProps<{ read: () => unknown; write: (value: any) => void }>()

const code = ref('')
const load = () => (code.value = JSON.stringify(props.read() ?? null, null, 2))
watch(() => JSON.stringify(props.read() ?? null), load, { immediate: true })

function apply() {
	try {
		props.write(JSON.parse(code.value))
	} catch (error) {
		toast.error(`${__('Not valid JSON')}: ${(error as Error).message}`)
	}
}
</script>

<template>
	<div
		class="flex h-full w-full flex-col gap-2"
		@keydown.meta.enter.prevent="apply"
		@keydown.ctrl.enter.prevent="apply"
	>
		<div class="flex items-center justify-between">
			<span class="text-p-sm text-ink-gray-5">JSON</span>
			<Button :label="__('Apply')" icon-left="lucide-check" @click="apply" />
		</div>
		<div class="flex min-h-0 flex-1 overflow-auto rounded-4 border border-outline-gray-2">
			<Code v-model="code" language="javascript" :autofocus="false" />
		</div>
	</div>
</template>
