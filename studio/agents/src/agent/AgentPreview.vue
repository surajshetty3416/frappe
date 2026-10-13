<template>
	<div class="flex h-full flex-col bg-surface-base">
		<div v-if="agent.error" class="flex flex-1 flex-col items-center justify-center px-6 text-center">
			<span class="lucide-triangle-alert size-5 text-ink-gray-4" />
			<p class="mt-3 text-base font-medium text-ink-gray-8">This agent could not open</p>
			<p class="mt-1 max-w-sm text-p-sm text-ink-gray-5">{{ agent.error }}</p>
		</div>
		<div v-else-if="!doc" class="flex flex-col gap-3 p-4">
			<Skeleton v-for="i in 4" :key="i" class="h-8 w-full rounded-4" />
		</div>
		<template v-else>
			<div class="flex h-11 shrink-0 items-center gap-2 border-b border-outline-gray-1 px-3">
				<span class="lucide-bot size-4 shrink-0 text-ink-gray-5" />
				<p class="min-w-0 flex-1 truncate text-sm text-ink-gray-6">{{ doc.description || "No description" }}</p>
				<span class="shrink-0 text-sm text-ink-gray-5">{{ doc.model }} · {{ toolCount }}</span>
				<Button variant="ghost" icon-left="lucide-rotate-ccw" label="New test" @click="chat?.restart()" />
			</div>
			<TestChat ref="chat" :key="doc.name" class="min-h-0 flex-1" :agent="doc.name" :title="doc.title" :modified="doc.modified" />
		</template>
	</div>
</template>

<script setup lang="ts">
import { Button, Skeleton } from "frappe-ui"
import { computed, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"

import { agent, open, preview } from "./state"
import TestChat from "./TestChat.vue"

const route = useRoute()
preview.router = useRouter()

const chat = ref<{ restart: () => void } | null>(null)
const name = computed(() => String(route.params.agent ?? ""))
const doc = computed(() => (agent.doc?.name === name.value ? agent.doc : null))
const toolCount = computed(() => {
	const count = doc.value?.tools.length ?? 0
	return `${count} tool${count === 1 ? "" : "s"}`
})

watch(
	name,
	(value) => {
		if (!value) return
		document.title = value
		if (value !== agent.doc?.name) open(value)
	},
	{ immediate: true }
)
</script>
