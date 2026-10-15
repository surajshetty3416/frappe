<template>
	<Dialog v-model:open="searchOpen" bare position="top" size="lg">
		<div data-layer="shell" class="flex flex-col">
			<div class="border-b border-outline-gray-1 p-2">
				<TextInput
					ref="input"
					v-model="query"
					variant="ghost"
					size="md"
					placeholder="Search projects, chats and artifacts"
					@keydown.enter="pick(results[0])"
				>
					<template #prefix><span class="lucide-search size-4 text-ink-gray-5" /></template>
				</TextInput>
			</div>
			<div class="max-h-[60vh] overflow-y-auto p-2">
				<p v-if="!results.length" class="px-2 py-6 text-center text-sm text-ink-gray-5">Nothing matches.</p>
				<template v-for="group in groups" :key="group.label">
					<p class="px-2 pb-1 pt-2 text-xs font-medium text-ink-gray-4 first:pt-0">{{ group.label }}</p>
					<SidebarItem
						v-for="result in group.results"
						:key="result.key"
						:label="result.title"
						:icon="result.icon"
						:route="result.route"
						:active="result === results[0]"
						@click="searchOpen = false"
					>
						<template #suffix><span class="mr-2 whitespace-nowrap text-xs text-ink-gray-4">{{ ago(result.modified) }}</span></template>
					</SidebarItem>
				</template>
			</div>
		</div>
	</Dialog>
</template>

<script setup lang="ts">
import { Dialog, SidebarItem, TextInput, dayjs } from "frappe-ui"
import { computed, nextTick, ref, watch } from "vue"
import { type RouteLocationRaw, useRouter } from "vue-router"

import { artifactIcon } from "../artifacts"
import { chatRoute, chats } from "../chats"
import { searchOpen } from "../layout"
import { projectRoute, projects } from "../projects"

const router = useRouter()
const query = ref("")
const input = ref<{ focus: () => void } | null>(null)

watch(searchOpen, (open) => {
	if (!open) return
	query.value = ""
	nextTick(() => input.value?.focus())
})

const entries = computed(() => {
	const artifacts = new Map<string, { key: string; title: string; icon: string; route: RouteLocationRaw; kind: string; modified: string }>()
	for (const chat of chats.value) {
		for (const artifact of chat.artifacts) {
			const key = `${artifact.doctype}/${artifact.name}`
			if (!artifacts.has(key)) {
				artifacts.set(key, {
					key,
					title: artifact.title,
					icon: artifactIcon(artifact),
					route: `${artifact.route}?chat=${chat.name}`,
					kind: "Artifacts",
					modified: chat.modified,
				})
			}
		}
	}
	const chatEntries = chats.value.map((chat) => ({
		key: chat.name,
		title: chat.title || "Untitled chat",
		icon: "lucide-message-square",
		route: chatRoute(chat.name),
		kind: "Chats",
		modified: chat.modified,
	}))
	const projectEntries = projects.value.map((project) => ({
		key: project.name,
		title: project.title,
		icon: "lucide-folder",
		route: projectRoute(project.name),
		kind: "Projects",
		modified: project.modified,
	}))
	return [...projectEntries, ...artifacts.values(), ...chatEntries]
})

const results = computed(() => {
	const words = query.value.toLowerCase().split(/\s+/).filter(Boolean)
	return entries.value.filter((entry) => words.every((word) => entry.title.toLowerCase().includes(word))).slice(0, 30)
})

// Enter opens the first result, so it shows as the active one
const groups = computed(() =>
	["Projects", "Artifacts", "Chats"]
		.map((label) => ({ label, results: results.value.filter((result) => result.kind === label) }))
		.filter((group) => group.results.length)
)
const ago = (modified: string) => dayjs(modified).fromNow()

function pick(result?: { route: RouteLocationRaw }) {
	if (!result) return
	searchOpen.value = false
	router.push(result.route)
}
</script>
