<template>
	<Dialog
		v-model:open="open"
		:title="user ? `Roles for ${user.full_name || user.name}` : 'Invite a person'"
		size="md"
		:actions="[{ label: user ? 'Save' : 'Send invite', variant: 'solid', disabled: !valid, onClick: save }]"
		@after-leave="emit('close')"
	>
		<div class="flex flex-col gap-4">
			<FormControl v-if="!user" v-model="email" type="email" label="Email" placeholder="name@example.com" description="They get an email to set their password." autofocus />
			<MultiSelect v-model="roles" label="Roles" :options="options" placeholder="Pick roles" />
		</div>
	</Dialog>
</template>

<script setup lang="ts">
import { Dialog, FormControl, MultiSelect, toast } from "frappe-ui"
import { computed, ref } from "vue"

import { type Person, errorMessage, getRoles, invite, setRoles } from "./people"

const props = defineProps<{ user: Person | null }>()
const emit = defineEmits<{ close: []; saved: [] }>()

const open = ref(true)
const email = ref("")
const roles = ref<string[]>(props.user ? [...props.user.roles] : [])
const options = ref<{ label: string; value: string }[]>([])
getRoles().then((names) => (options.value = names.map((name) => ({ label: name, value: name }))))

const valid = computed(() => (props.user || /^\S+@\S+\.\S+$/.test(email.value.trim())) && roles.value.length > 0)

async function save() {
	try {
		if (props.user) await setRoles(props.user.name, roles.value)
		else await invite(email.value.trim(), roles.value)
	} catch (error) {
		return toast.error(errorMessage(error))
	}
	toast.success(props.user ? "Roles saved" : `Invited ${email.value.trim()}`)
	emit("saved")
	open.value = false
}
</script>
