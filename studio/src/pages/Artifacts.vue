<template>
	<div data-layer="shell" class="h-full overflow-y-auto bg-surface-base">
		<div class="mx-auto flex w-full max-w-[1040px] flex-col gap-6 px-6 py-10">
			<header class="flex flex-wrap items-center gap-2">
				<h1 class="mr-auto text-3xl font-semibold text-ink-gray-9">{{ kind.title }}</h1>
				<ProjectPicker v-model="project" all-label="All projects" />
				<ArtifactViewToggle />
				<Button variant="solid" icon-left="lucide-square-pen" label="New chat" :route="newChatRoute(project ?? activeProject)" />
			</header>
			<div v-if="!artifacts" class="flex h-24 items-center justify-center">
				<LoadingIndicator class="size-4 text-ink-gray-5" />
			</div>
			<ProjectEmpty
				v-else-if="!artifacts.length"
				:title="project ? `No ${kind.title.toLowerCase()} in ${projectTitle(project)} yet` : `No ${kind.title.toLowerCase()} yet`"
				text="Ask for one in a chat. What the chats make shows here."
			/>
			<ArtifactGrid v-else :artifacts="artifacts" :show-project="!project" />
		</div>
	</div>
</template>

<script setup lang="ts">
import { useDebounceFn } from "@vueuse/core"
import { Button, LoadingIndicator } from "frappe-ui"
import { computed, onBeforeUnmount, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"

import { artifactKind, artifactKinds } from "../artifacts"
import ArtifactGrid from "../components/ArtifactGrid.vue"
import ArtifactViewToggle from "../components/ArtifactViewToggle.vue"
import ProjectPicker from "../components/ProjectPicker.vue"
import ProjectEmpty from "../components/project/ProjectEmpty.vue"
import { type ProjectArtifact, activeProject, getArtifacts, newChatRoute, projectTitle } from "../projects"
import { onListUpdate } from "../realtime"

// every app, website or dashboard the person can open, or only what one project made
const route = useRoute()
const router = useRouter()
const kind = computed(() => artifactKind(route) ?? artifactKinds[0])
const project = computed({
	get: () => (typeof route.query.project === "string" ? route.query.project : null),
	set: (value) => router.replace({ query: value ? { project: value } : {} }),
})

const artifacts = ref<ProjectArtifact[] | null>(null)
async function load() {
	const wanted = [kind.value, project.value]
	const list = await getArtifacts(kind.value.doctypes, project.value).catch(() => [])
	if (wanted[0] === kind.value && wanted[1] === project.value) artifacts.value = list
}
watch(
	[kind, project],
	() => {
		artifacts.value = null
		document.title = `${kind.value.title} · Studio`
		load()
	},
	{ immediate: true }
)

const reload = useDebounceFn(load, 500)
const stops = ["Studio Project", ...artifactKinds.flatMap((each) => each.doctypes)].map((doctype) => onListUpdate(doctype, reload))
onBeforeUnmount(() => stops.forEach((stop) => stop()))
</script>
