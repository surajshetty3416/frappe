<template>
	<div v-if="doc" class="flex flex-col gap-4 p-4">
		<EnabledField doctype="Flow Agent" :name="doc.name" :enabled="Boolean(doc.enabled)" :reload="() => open(doc!.name)" />
		<FormControl v-model="description" type="textarea" label="Description" :rows="3" @blur="save('description', description)" />
		<FormControl v-model="instructions" type="textarea" label="Instructions" :rows="10" @blur="save('instructions', instructions)" />
		<div>
			<p class="mb-1.5 text-xs text-ink-gray-5">Tools</p>
			<div class="flex flex-wrap gap-1 text-sm text-ink-gray-8">
				<span v-for="tool in tools" :key="tool" class="rounded-4 bg-surface-gray-2 px-1.5 py-0.5">{{ tool }}</span>
				<span v-if="!tools.length">None</span>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { FormControl, toast } from "frappe-ui"
import { computed, ref, watch } from "vue"

import { errorText, getToolTitles, setValue } from "../api"
import EnabledField from "../components/EnabledField.vue"
import { agent, open } from "./state"

const doc = computed(() => agent.doc)
const description = ref("")
const instructions = ref("")
const titles = ref<Record<string, string>>({})

watch(
	doc,
	(value) => {
		description.value = value?.description ?? ""
		instructions.value = value?.instructions ?? ""
	},
	{ immediate: true }
)

async function save(field: "description" | "instructions", value: string) {
	if (!doc.value || (doc.value[field] ?? "") === value) return
	try {
		await setValue("Flow Agent", doc.value.name, { [field]: value })
		await open(doc.value.name)
	} catch (error) {
		toast.error(errorText(error))
	}
}

const sentence = (value: string) => value.charAt(0).toUpperCase() + value.slice(1).toLowerCase()
const tools = computed(() => (doc.value?.tools ?? []).map((row) => sentence(titles.value[row.tool] ?? row.tool.replaceAll("_", " "))))

watch(
	() => doc.value?.tools.map((row) => row.tool).join(),
	async () => {
		const names = doc.value?.tools.map((row) => row.tool) ?? []
		if (names.length) titles.value = Object.fromEntries((await getToolTitles(names)).map((row) => [row.name, row.title]))
	},
	{ immediate: true }
)
</script>
