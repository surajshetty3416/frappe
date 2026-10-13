<template>
	<div class="flex flex-col gap-4 p-4">
		<TextInput
			label="Subject"
			:model-value="String(state.doc?.subject ?? '')"
			@change="set('subject', ($event.target as HTMLInputElement).value.trim())"
		/>
	</div>
</template>

<script setup lang="ts">
import type { OutputState, SetField } from "@web/output/outputEditor"
import { TextInput } from "frappe-ui"

defineProps<{ state: OutputState; set: SetField }>()
</script>
