<template>
	<Dialog
		v-model:open="doctype.demoData"
		title="Demo data"
		icon="lucide-sparkles"
		size="sm"
		:actions="[{ label: 'Ask the assistant', variant: 'solid', disabled: !valid, onClick: ask }]"
	>
		<p class="mb-4 text-p-base text-ink-gray-6">The assistant writes realistic {{ doctype.name }} records in the chat, linked to records that already exist.</p>
		<FormControl v-model="count" type="number" label="How many records" :min="1" :max="1000" autofocus @keydown.enter="valid && ask()" />
	</Dialog>
</template>

<script setup lang="ts">
import { Dialog, FormControl } from "frappe-ui"
import { computed, ref } from "vue"
import { useRouter } from "vue-router"

import { askChat } from "../chat"
import { doctype } from "../doctype"

const router = useRouter()
const count = ref<string | number>(20)
const valid = computed(() => Number(count.value) >= 1 && Number(count.value) <= 1000)

function ask() {
	const message = `Add ${Number(count.value)} realistic demo records to ${doctype.name}. Fill every field with believable, varied values, and link only to records that exist.`
	doctype.demoData = false
	if (askChat(message)) return
	router.push({ name: "studio-chat", params: { session: "new" }, query: { prompt: message } })
}
</script>
