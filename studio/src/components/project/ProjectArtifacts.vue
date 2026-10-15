<template>
	<ProjectEmpty
		v-if="!page.artifacts.length"
		title="Nothing made yet"
		text="The DocTypes, apps, web pages, dashboards, print formats, emails and agents this project's chats make show here."
	>
		<Button v-for="idea in IDEAS" :key="idea.text" variant="outline" :icon-left="idea.icon" @click="emit('prefill', idea.text)">
			{{ idea.text.trim() }}<span class="text-ink-gray-4">…</span>
		</Button>
	</ProjectEmpty>
	<ArtifactGrid v-else :artifacts="page.artifacts" />
</template>

<script setup lang="ts">
import { Button } from "frappe-ui"

import type { ProjectPage } from "../../projects"
import ArtifactGrid from "../ArtifactGrid.vue"
import ProjectEmpty from "./ProjectEmpty.vue"

defineProps<{ page: ProjectPage }>()
const emit = defineEmits<{ prefill: [text: string] }>()

// each waits for the rest of its sentence
const IDEAS = [
	{ icon: "lucide-database", text: "A DocType for " },
	{ icon: "lucide-globe", text: "A website for " },
	{ icon: "lucide-chart-column", text: "A dashboard of " },
]
</script>
