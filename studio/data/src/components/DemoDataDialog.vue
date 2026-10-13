<template>
	<Dialog v-model:open="doctype.demoData" title="Demo data" icon="lucide-sparkles" size="sm">
		<p class="mb-4 text-p-base text-ink-gray-6">
			The assistant adds {{ valid ? Number(count) : "" }} realistic {{ doctype.name }} records, linking only to records that exist.
		</p>
		<FormControl v-model="count" type="number" label="How many records" :min="1" :max="1000" autofocus @keydown.enter="valid && ask()" />
		<template #actions>
			<div class="flex justify-end">
				<Button variant="solid" label="Ask the assistant" :disabled="!valid" @click="ask" />
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { sendToChat } from "@shell/editor"
import { Button, Dialog, FormControl } from "frappe-ui"
import { computed, ref } from "vue"
import { useRouter } from "vue-router"

import { doctype } from "../doctype"

const router = useRouter()
const count = ref<string | number>(20)
const valid = computed(() => Number(count.value) >= 1 && Number(count.value) <= 1000)

function ask() {
	const message = `Add ${Number(count.value)} realistic demo records to ${doctype.name}. Fill every field with believable, varied values, and link only to records that exist.`
	doctype.demoData = false
	if (sendToChat(message)) return
	router.push({ name: "studio-chat", params: { session: "new" }, query: { prompt: message } })
}
</script>
