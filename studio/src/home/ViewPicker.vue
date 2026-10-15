<template>
	<Dialog v-model:open="open" bare position="top" size="lg">
		<div data-layer="shell" class="flex flex-col">
			<div class="border-b border-outline-gray-1 p-2">
				<TextInput ref="input" v-model="query" variant="ghost" size="md" placeholder="Find a view to show on the home">
					<template #prefix><span class="lucide-search size-4 text-ink-gray-5" /></template>
				</TextInput>
			</div>
			<div class="max-h-[60vh] overflow-y-auto p-2">
				<p v-if="!matches.length" class="px-2 py-6 text-center text-sm text-ink-gray-5">Nothing matches.</p>
				<SidebarItem
					v-for="artifact in matches"
					:key="`${artifact.doctype}/${artifact.name}`"
					:label="artifact.title"
					:icon="artifactIcon(artifact)"
					@click="pick(artifact)"
				>
					<template #suffix><span class="mr-2 text-xs text-ink-gray-4">{{ artifact.label }}</span></template>
				</SidebarItem>
			</div>
		</div>
	</Dialog>
</template>

<script setup lang="ts">
import { Dialog, SidebarItem, TextInput } from "frappe-ui"
import { computed, nextTick, ref, watch } from "vue"

import { artifactIcon, artifactKinds } from "../artifacts"
import { type ProjectArtifact, getArtifacts } from "../projects"
import type { HomeArtifact } from "./home"

const open = defineModel<boolean>("open", { required: true })
const emit = defineEmits<{ pick: [artifact: HomeArtifact] }>()

const query = ref("")
const input = ref<{ focus: () => void } | null>(null)
const everything = ref<ProjectArtifact[]>([])

watch(open, async (opened) => {
	if (!opened) return
	query.value = ""
	nextTick(() => input.value?.focus())
	everything.value = await getArtifacts(
		artifactKinds.flatMap((kind) => kind.doctypes),
		null
	).catch(() => [])
})

const matches = computed(() => {
	const words = query.value.trim().toLowerCase().split(/\s+/).filter(Boolean)
	return everything.value.filter((artifact) => words.every((word) => artifact.title.toLowerCase().includes(word)))
})

function pick(artifact: HomeArtifact) {
	emit("pick", artifact)
	open.value = false
}
</script>
