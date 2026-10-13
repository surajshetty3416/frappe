<template>
	<Dialog
		v-model:open="open"
		:title="user ? `Roles for ${displayName(user)}` : 'Invite a person'"
		size="md"
		:actions="[
			{ label: 'Cancel', variant: 'ghost' },
			{ label: user ? 'Save' : 'Send invite', variant: 'solid', disabled: !valid, onClick: save },
		]"
		@after-leave="emit('close')"
	>
		<div class="flex flex-col gap-4">
			<FormControl v-if="!user" v-model="email" type="email" label="Email" placeholder="name@example.com" description="They get an email to set their password." autofocus />
			<div :autofocus="user ? true : undefined">
				<MultiSelect v-model="selected" label="Roles" :options="options" placeholder="Pick roles">
					<template #summary="{ selectedOptions, summary }">
						<span v-if="selectedOptions.length" class="flex gap-1">
							<Badge v-for="option in selectedOptions" :key="option.value" :label="option.label" variant="outline" class="bg-surface-base" />
						</span>
						<template v-else>{{ summary }}</template>
					</template>
				</MultiSelect>
			</div>
		</div>
	</Dialog>
</template>

<script setup lang="ts">
import { Badge, Dialog, FormControl, MultiSelect, toast } from "frappe-ui"
import { computed, ref } from "vue"

import { type Person, displayName, errorMessage, invite, setRoles, toastOptions } from "./people"

const props = defineProps<{ user: Person | null; roles: string[] }>()
const emit = defineEmits<{ close: []; saved: [] }>()

const open = ref(true)
const email = ref("")
const selected = ref<string[]>(props.user ? [...props.user.roles] : [])
const options = computed(() => props.roles.map((name) => ({ label: name, value: name })))

const valid = computed(() => (props.user || /^\S+@\S+\.\S+$/.test(email.value.trim())) && selected.value.length > 0)

async function save() {
	try {
		if (props.user) await setRoles(props.user.name, selected.value)
		else await invite(email.value.trim(), selected.value)
	} catch (error) {
		return toast.error(errorMessage(error), toastOptions)
	}
	toast.success(props.user ? "Roles saved" : `Invited ${email.value.trim()}`, toastOptions)
	emit("saved")
	open.value = false
}
</script>
