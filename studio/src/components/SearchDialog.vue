<template>
	<Dialog v-model:open="searchOpen" bare position="top" size="lg">
		<div data-layer="shell" class="flex flex-col">
			<div class="border-b border-outline-gray-1 p-2">
				<TextInput
					ref="input"
					v-model="query"
					variant="ghost"
					size="md"
					placeholder="Search chats and artifacts"
					@keydown.enter="pick(results[0])"
				>
					<template #prefix><span class="lucide-search size-4 text-ink-gray-5" /></template>
				</TextInput>
			</div>
			<div class="max-h-[60vh] overflow-y-auto p-2">
				<p v-if="!results.length" class="px-2 py-6 text-center text-sm text-ink-gray-5">Nothing matches.</p>
				<SidebarItem
					v-for="result in results"
					:key="result.key"
					:label="result.title"
					:icon="result.icon"
					:route="result.route"
					@click="searchOpen = false"
				>
					<template #suffix><span class="mr-2 text-xs text-ink-gray-4">{{ result.kind }}</span></template>
				</SidebarItem>
			</div>
		</div>
	</Dialog>
</template>

<script setup lang="ts">
import { Dialog, SidebarItem, TextInput } from "frappe-ui"
import { computed, nextTick, ref, watch } from "vue"
import { useRouter } from "vue-router"

import { artifactIcon, artifactLabel } from "../artifacts"
import { chats } from "../chats"
import { searchOpen } from "../layout"

const router = useRouter()
const query = ref("")
const input = ref<{ focus: () => void } | null>(null)

watch(searchOpen, (open) => {
	if (!open) return
	query.value = ""
	nextTick(() => input.value?.focus())
})

const entries = computed(() => {
	const artifacts = new Map<string, { key: string; title: string; icon: string; route: string; kind: string }>()
	for (const chat of chats.value) {
		for (const artifact of chat.artifacts) {
			const key = `${artifact.doctype}/${artifact.name}`
			if (!artifacts.has(key)) {
				artifacts.set(key, {
					key,
					title: artifact.title,
					icon: artifactIcon(artifact),
					route: `${artifact.route}?chat=${chat.name}`,
					kind: artifactLabel(artifact.doctype),
				})
			}
		}
	}
	const chatEntries = chats.value.map((chat) => ({
		key: chat.name,
		title: chat.title || "Untitled chat",
		icon: "lucide-message-square",
		route: `/studio/chat/${chat.name}`,
		kind: "Chat",
	}))
	return [...artifacts.values(), ...chatEntries]
})

const results = computed(() => {
	const words = query.value.toLowerCase().split(/\s+/).filter(Boolean)
	return entries.value.filter((entry) => words.every((word) => entry.title.toLowerCase().includes(word))).slice(0, 30)
})

function pick(result?: { route: string }) {
	if (!result) return
	searchOpen.value = false
	router.push(result.route)
}
</script>
