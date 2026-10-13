<template>
	<div class="flex flex-col">
		<Teleport defer to="#data-view-actions">
			<Combobox
				v-if="editable"
				class="w-52"
				:model-value="null"
				:options="roleOptions"
				placeholder="Add a role…"
				open-on-focus
				@update:model-value="(role) => role && addRole(String(role))"
			/>
		</Teleport>

		<div class="min-h-0 flex-1 overflow-y-auto px-3 pb-6 pt-3">
			<div :class="GRID" class="h-8 rounded-4 bg-surface-gray-2 px-2 text-sm text-ink-gray-5">
				<span>Role</span>
				<span v-for="type in PERM_TYPES" :key="type" class="text-center capitalize">{{ type }}</span>
				<span />
			</div>
			<div v-if="!rows.length" class="flex flex-col items-center px-6 py-12 text-center">
				<span class="lucide-shield size-5 text-ink-gray-4" />
				<p class="mt-3 text-base font-medium text-ink-gray-8">Nobody has access yet</p>
				<p class="mt-1 max-w-sm text-p-sm text-ink-gray-5">Add a role to say who can read, write, create and delete these records.</p>
			</div>
			<div v-for="perm in rows" :key="perm.name ?? perm.role" :class="GRID" class="group h-11 border-b border-outline-gray-1 px-2" data-selection-ui>
				<span class="flex min-w-0 items-center gap-2">
					<span class="lucide-users size-4 shrink-0 text-ink-gray-5" />
					<span class="truncate text-base text-ink-gray-8">{{ perm.role }}</span>
				</span>
				<span v-for="type in PERM_TYPES" :key="type" class="flex justify-center">
					<Tooltip :text="type === 'submit' && !doctype.doc?.is_submittable ? 'Records of this DocType are not submitted' : undefined">
						<Checkbox
							:model-value="Boolean(perm[type])"
							:disabled="!editable || (type === 'submit' && !doctype.doc?.is_submittable)"
							:aria-label="`${perm.role} can ${type}`"
							@update:model-value="(value) => setPerm(perm, type, Boolean(value))"
						/>
					</Tooltip>
				</span>
				<span class="flex justify-end">
					<Button
						v-if="editable"
						variant="ghost"
						icon="lucide-trash-2"
						tooltip="Remove role"
						class="opacity-0 group-hover:opacity-100 focus-visible:opacity-100"
						@click="removeRole(perm)"
					/>
				</span>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { Button, Checkbox, Combobox, Tooltip } from "frappe-ui"
import { computed, ref } from "vue"

import { type DocPerm, PERM_TYPES, type PermType, getNames } from "../api"
import { change, doctype, editable } from "../doctype"

const GRID = "grid grid-cols-[minmax(0,1fr)_repeat(5,64px)_32px] items-center gap-2"

// field-level permissions (permlevel above 0) stay as they are; the agent manages those
const rows = computed(() => (doctype.doc?.permissions ?? []).filter((perm) => !perm.permlevel))

const roles = ref<string[]>([])
getNames("Role").then((names) => (roles.value = names))
const roleOptions = computed(() => {
	const taken = new Set(rows.value.map((perm) => perm.role))
	return roles.value.filter((role) => !taken.has(role)).map((role) => ({ label: role, value: role }))
})

function setPerm(perm: DocPerm, type: PermType, value: boolean) {
	change(() => {
		perm[type] = value ? 1 : 0
		// writing, creating and deleting all start from reading
		if (value && type !== "read") perm.read = 1
	})
}

const addRole = (role: string) => change((doc) => doc.permissions.push({ role, permlevel: 0, read: 1 }))
const removeRole = (perm: DocPerm) => change((doc) => (doc.permissions = doc.permissions.filter((other) => other !== perm)))
</script>
