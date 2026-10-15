<template>
	<Dialog
		v-model:open="open"
		title="New skill"
		size="xl"
		:actions="[
			{ label: 'Cancel', variant: 'ghost' },
			{ label: 'Create skill', variant: 'solid', disabled: !valid, onClick: create },
		]"
	>
		<div data-layer="shell" class="flex flex-col gap-4">
			<FormControl v-model="title" label="Name" placeholder="Conference house style" autofocus />
			<FormControl
				v-model="description"
				label="When should a chat use it?"
				placeholder="When writing anything attendees or sponsors will read"
			/>
			<FormControl
				v-model="instructions"
				type="textarea"
				label="Instructions"
				:rows="10"
				placeholder="Call the event Frappeverse 2027, never &quot;the conference&quot;. Dates read 20–21 August 2027. Prices are in INR with the ₹ sign."
			/>
		</div>
	</Dialog>
</template>

<script setup lang="ts">
import { Dialog, FormControl, call, toast } from "frappe-ui"
import { computed, ref, watch } from "vue"

import { errorText } from "../../projects"

const open = defineModel<boolean>("open", { required: true })
const emit = defineEmits<{ created: [skill: string] }>()
const title = ref("")
const description = ref("")
const instructions = ref("")
const valid = computed(() => Boolean(title.value.trim() && description.value.trim() && instructions.value.trim()))

watch(open, (opened) => {
	if (!opened) return
	title.value = description.value = instructions.value = ""
})

async function create() {
	try {
		const doc = await call<{ name: string }>("frappe.client.insert", {
			doc: {
				doctype: "Flow Skill",
				title: title.value.trim(),
				description: description.value.trim(),
				instructions: instructions.value.trim(),
				enabled: 1,
				user_invocable: 1,
			},
		})
		open.value = false
		emit("created", doc.name)
	} catch (error) {
		toast.error(errorText(error))
	}
}
</script>
