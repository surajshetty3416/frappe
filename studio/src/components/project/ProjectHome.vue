<template>
	<p v-if="projectPageFailed" class="px-2 text-base text-ink-gray-7">This project is gone, or it is not shared with you.</p>
	<div v-else-if="!projectPage" class="flex h-24 items-center justify-center">
		<LoadingIndicator class="size-4 text-ink-gray-5" />
	</div>
	<div v-else class="flex flex-col gap-8">
		<RunningChats :project="project" />
		<div class="flex flex-col gap-3">
			<div class="flex items-center justify-between gap-2">
				<TabButtons :model-value="tab" :options="tabs">
					<template #suffix="{ button }">
						<span v-if="count(button.value)" class="text-ink-gray-4">{{ count(button.value) }}</span>
					</template>
				</TabButtons>
				<ArtifactViewToggle v-if="tab === 'artifacts' && projectPage.artifacts.length" />
				<AddSkill v-else-if="tab === 'skills' && projectPage.project.can_write" :page="projectPage" @changed="load" />
			</div>
			<component :is="section" :page="projectPage" @changed="load" @prefill="(text: string) => emit('prefill', text)" />
		</div>
	</div>
</template>

<script setup lang="ts">
import { useDebounceFn } from "@vueuse/core"
import { LoadingIndicator, TabButtons } from "frappe-ui"
import { computed, onBeforeUnmount, watch } from "vue"
import { useRoute } from "vue-router"

import { loadProjectPage, projectPage, projectPageFailed, projectRoute } from "../../projects"
import { onListUpdate } from "../../realtime"
import ArtifactViewToggle from "../ArtifactViewToggle.vue"
import AddSkill from "./AddSkill.vue"
import ProjectArtifacts from "./ProjectArtifacts.vue"
import ProjectSkills from "./ProjectSkills.vue"
import RunningChats from "./RunningChats.vue"

const SECTIONS = {
	artifacts: { label: "Artifacts", component: ProjectArtifacts },
	skills: { label: "Skills", component: ProjectSkills },
}
type Section = keyof typeof SECTIONS

// what sits under a project's chatbox: its chats at work, then what it made and the skills its chats use
const props = defineProps<{ project: string }>()
const emit = defineEmits<{ prefill: [text: string] }>()
const route = useRoute()
const tab = computed(() => (route.params.tab || "artifacts") as Section)
const section = computed(() => SECTIONS[tab.value].component)

const load = () => loadProjectPage(props.project)
watch(
	() => props.project,
	() => {
		projectPage.value = null
		projectPageFailed.value = false
		load()
	},
	{ immediate: true }
)
watch(projectPage, (page) => page && (document.title = `${page.project.title} · Studio`))
// the page follows what the project's chats make elsewhere
const reload = useDebounceFn(load, 500)
const stops = ["Studio Project", "Flow Session"].map((doctype) => onListUpdate(doctype, reload))
onBeforeUnmount(() => stops.forEach((stop) => stop()))

const count = (key: string | number) => {
	if (!projectPage.value) return 0
	if (key === "skills") return projectPage.value.skills.filter((skill) => skill.own).length
	return projectPage.value.artifacts.length
}
const tabs = computed(() =>
	(Object.keys(SECTIONS) as Section[]).map((key) => ({
		value: key,
		label: SECTIONS[key].label,
		route: projectRoute(props.project, key),
	}))
)
</script>
