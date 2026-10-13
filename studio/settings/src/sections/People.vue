<template>
	<SettingsHeader title="People" description="Who signs in to this site, and what their roles let them do.">
		<template #actions>
			<Button variant="solid" icon-left="lucide-user-plus" label="Invite" @click="dialog = { user: null }" />
		</template>
	</SettingsHeader>
	<SettingsBody>
		<div v-if="!users" class="flex h-24 items-center justify-center">
			<LoadingIndicator class="size-4 text-ink-gray-4" />
		</div>
		<ul v-else class="mt-6 divide-y divide-outline-gray-1 rounded-6 border border-outline-gray-1">
			<li v-for="user in users" :key="user.name" class="flex h-14 items-center gap-3 px-3">
				<Avatar :label="user.full_name || user.name" :image="user.user_image" size="lg" />
				<div class="min-w-0 flex-1">
					<div class="flex items-center gap-2">
						<span class="truncate text-base font-medium text-ink-gray-8">{{ user.full_name || user.name }}</span>
						<Badge v-if="!user.enabled" label="Disabled" size="sm" />
					</div>
					<div class="mt-0.5 truncate text-sm text-ink-gray-5">{{ user.email }}</div>
				</div>
				<Tooltip :text="user.roles.join(', ')" :disabled="user.roles.length < 3">
					<span class="max-w-[240px] truncate text-sm text-ink-gray-6">{{ rolesSummary(user) }}</span>
				</Tooltip>
				<Dropdown v-if="user.name !== 'Administrator'" :options="menu(user)" align="end">
					<Button variant="ghost" icon="lucide-ellipsis" :aria-label="`Actions for ${user.name}`" />
				</Dropdown>
				<span v-else class="w-7" />
			</li>
		</ul>
	</SettingsBody>
	<RolesDialog v-if="dialog" :user="dialog.user" @close="dialog = null" @saved="load" />
</template>

<script setup lang="ts">
import {
	Avatar,
	Badge,
	Button,
	Dropdown,
	LoadingIndicator,
	SettingsBody,
	SettingsHeader,
	Tooltip,
	call,
	toast,
} from "frappe-ui"
import { ref } from "vue"

import RolesDialog from "./RolesDialog.vue"
import { type Person, getPeople } from "./people"

const users = ref<Person[] | null>(null)
const dialog = ref<{ user: Person | null } | null>(null)

async function load() {
	users.value = await getPeople()
}
load()

function rolesSummary(user: Person) {
	if (user.name === "Administrator") return "All roles"
	if (!user.roles.length) return "No roles"
	if (user.roles.length < 3) return user.roles.join(", ")
	return `${user.roles.slice(0, 2).join(", ")} +${user.roles.length - 2}`
}

function menu(user: Person) {
	return [
		{ label: "Change roles", icon: "lucide-shield", onClick: () => (dialog.value = { user }) },
		user.enabled
			? { label: "Disable", icon: "lucide-user-x", onClick: () => setEnabled(user, 0) }
			: { label: "Enable", icon: "lucide-user-check", onClick: () => setEnabled(user, 1) },
	]
}

async function setEnabled(user: Person, enabled: 0 | 1) {
	await call("frappe.client.set_value", { doctype: "User", name: user.name, fieldname: "enabled", value: enabled })
	toast.success(enabled ? `${user.name} can sign in again` : `${user.name} can no longer sign in`)
	load()
}
</script>
