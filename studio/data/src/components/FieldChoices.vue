<template>
	<p class="pb-1.5 text-xs text-ink-gray-5">One option per line</p>
	<Textarea v-model="text" :rows="6" autofocus />
</template>

<script setup lang="ts">
import { Textarea } from "frappe-ui"
import { onBeforeUnmount, ref } from "vue"

import { change, fieldOf } from "../doctype"

const props = defineProps<{ id: string }>()

const text = ref((fieldOf(props.id)?.options || "").split("\n").filter(Boolean).join("\n"))

// the popover closing is the edit's end, saved as one change
onBeforeUnmount(() => {
	const field = fieldOf(props.id)
	const options = text.value
		.split("\n")
		.map((choice) => choice.trim())
		.filter(Boolean)
		.join("\n")
	if (field && options !== (field.options || "")) change(() => (field.options = options))
})
</script>
