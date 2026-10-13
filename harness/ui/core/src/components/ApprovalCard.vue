<template>
	<div class="flex max-h-[min(480px,70vh)] flex-col overflow-hidden rounded-6 border border-outline-gray-2 bg-surface-base">
		<div class="flex items-start gap-2 px-3 py-2.5">
			<span class="lucide-shield-check mt-0.5 size-4 flex-none text-ink-gray-5" />
			<div class="min-w-0 flex-1 text-base text-ink-gray-8">{{ title }}</div>
			<span v-if="total > 1" class="flex-none text-sm text-ink-gray-5">{{ position }} of {{ total }}</span>
		</div>
		<div v-if="presentation.argsComponent" class="overflow-y-auto border-y border-outline-gray-1">
			<component :is="presentation.argsComponent" :arguments="args" />
		</div>
		<pre
			v-else-if="body"
			class="m-0 max-h-[240px] overflow-auto border-y border-outline-gray-1 bg-surface-gray-1 px-3 py-2 font-mono text-xs leading-relaxed text-ink-gray-6"
			>{{ body }}</pre
		>
		<div class="flex items-center justify-end gap-2 px-3 py-2.5">
			<Button label="Deny" @click="flow.answerApproval(call.id, 'Deny')" />
			<Button variant="solid" label="Allow" @click="flow.answerApproval(call.id, 'Approve')" />
		</div>
	</div>
</template>

<script setup>
import { computed, inject } from "vue"
import { Button } from "frappe-ui"

// One gated call, answered here. A batch shows one call at a time.
const props = defineProps({
	call: { type: Object, required: true },
	position: { type: Number, default: 1 },
	total: { type: Number, default: 1 },
})
const flow = inject("flow")

const args = computed(() => props.call.args ?? props.call.arguments ?? {})
const presentation = computed(() => flow.options?.presentTool?.(props.call.name, args.value) ?? {})

const title = computed(() => {
	const custom = presentation.value.title
	if (custom != null) return custom
	if (presentation.value.label) return `${presentation.value.label}?`
	return props.call.prompt?.split("\n")[0] ?? `Allow ${props.call.name}?`
})

const body = computed(() => {
	const custom = presentation.value.body
	if (custom != null) return custom
	const rest = (props.call.prompt ?? "").split("\n").slice(1).join("\n").trim()
	return rest || JSON.stringify(args.value, null, 2)
})
</script>
