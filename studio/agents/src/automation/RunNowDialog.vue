<template>
	<Dialog
		v-model:open="automation.choosing"
		:title="`Run on a ${doctype}`"
		size="sm"
		@after-leave="docname = null"
	>
		<p class="mb-3 text-p-sm text-ink-gray-5">The automation runs once on the {{ doctype }} you choose.</p>
		<Combobox
			v-model="docname"
			class="w-full"
			:options="records"
			:loading="loading"
			:placeholder="`Choose a ${doctype}`"
			:empty-text="`No ${doctype} matches`"
			open-on-focus
		/>
		<template #actions>
			<div class="flex justify-end gap-2">
				<Button label="Cancel" @click="automation.choosing = false" />
				<Button variant="solid" label="Run" icon-left="lucide-play" :disabled="!docname" :loading="running" @click="submit" />
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { Button, Combobox, Dialog } from "frappe-ui"
import { ref, watch } from "vue"

import { getRecords } from "../api"
import { automation, run } from "./state"

defineProps<{ doctype: string }>()

const docname = ref<string | null>(null)
const records = ref<{ value: string; label: string }[]>([])
const loading = ref(false)
const running = ref(false)

async function load() {
	loading.value = true
	records.value = await getRecords(automation.name)
	loading.value = false
}

// the newest record is the likely one
watch(
	() => automation.choosing,
	async (choosing) => {
		if (!choosing) return
		await load()
		docname.value = records.value[0]?.value ?? null
	}
)

async function submit() {
	if (!docname.value) return
	running.value = true
	await run(docname.value)
	running.value = false
}
</script>
