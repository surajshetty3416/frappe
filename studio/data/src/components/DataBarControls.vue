<template>
	<Button v-if="view === 'fields'" variant="ghost" icon="lucide-plus" tooltip="Add field" aria-label="Add field" @click="addField" />
	<Combobox
		v-else-if="view === 'permissions'"
		:model-value="null"
		:options="roleOptions"
		placeholder="Find a role"
		@update:model-value="(role) => role && addRole(String(role))"
	>
		<template #trigger>
			<Button variant="ghost" icon="lucide-plus" tooltip="Add role" aria-label="Add role" />
		</template>
	</Combobox>
</template>

<script setup lang="ts">
import { Button, Combobox } from "frappe-ui"
import { computed, ref } from "vue"

import { getNames } from "../api"
import { addField, change, doctype, view } from "../doctype"

const roles = ref<string[]>([])
getNames("Role").then((names) => (roles.value = names))
const roleOptions = computed(() => {
	const taken = new Set((doctype.doc?.permissions ?? []).filter((perm) => !perm.permlevel).map((perm) => perm.role))
	return roles.value.filter((role) => !taken.has(role)).map((role) => ({ label: role, value: role }))
})

// DocPerm defaults every right below to 1, so a new role names each one it does not get
const addRole = (role: string) =>
	change((doc) =>
		doc.permissions.push({ role, permlevel: 0, read: 1, write: 0, create: 0, delete: 0, report: 0, export: 0, share: 0, print: 0, email: 0 })
	)
</script>
