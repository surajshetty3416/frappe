<template>
	<Dialog v-model:open="open" bare position="top" size="md">
		<div data-layer="shell" class="flex flex-col p-2">
			<p class="px-2 pb-1 pt-1.5 text-xs font-medium text-ink-gray-5">Switch persona</p>
			<button
				v-for="persona in personas"
				:key="persona.user"
				type="button"
				class="flex items-center gap-3 rounded-6 px-2 py-2 text-left hover:bg-surface-gray-1 disabled:opacity-60"
				:disabled="persona.user === me || switching !== null"
				@click="switchTo(persona.user)"
			>
				<Avatar :label="persona.title" size="md" />
				<span class="min-w-0 flex-1">
					<span class="block truncate text-sm font-medium text-ink-gray-8">{{ persona.title }}</span>
					<span class="block truncate text-sm text-ink-gray-5">{{ persona.role }}</span>
				</span>
				<span v-if="persona.user === me" class="text-xs text-ink-gray-4">You</span>
				<LoadingIndicator v-else-if="switching === persona.user" class="size-3.5 text-ink-gray-5" />
			</button>
		</div>
	</Dialog>
</template>

<script setup lang="ts">
import { Avatar, Dialog, LoadingIndicator, call } from "frappe-ui"
import { ref } from "vue"

import { sessionUser } from "../session"
import { personas } from "./home"

// for showing the demo: sign in as another persona, each a real account, without their password
const open = defineModel<boolean>("open", { required: true })
const me = sessionUser()
const switching = ref<string | null>(null)

async function switchTo(user: string) {
	switching.value = user
	await call("frappe.ai.demo.personas.switch_persona", { user })
	window.location.href = "/home"
}
</script>
