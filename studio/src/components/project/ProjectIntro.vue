<template>
	<div class="flex items-start gap-3">
		<div class="min-w-0 flex-1">
			<h1 class="text-3xl font-semibold text-ink-gray-9">What do you want to build in {{ projectTitle(project) }}?</h1>
			<p class="mt-1.5 text-p-base text-ink-gray-6">
				{{ projectPage?.project.description || "A website, a dashboard, an app, or any change to the data on this site." }}
			</p>
		</div>
		<template v-if="projectPage?.project.can_write">
			<Button variant="ghost" icon="lucide-pencil" tooltip="Edit project" @click="editing = true" />
			<ProjectDialog v-model:open="editing" :project="projectPage.project" />
		</template>
	</div>
</template>

<script setup lang="ts">
import { Button } from "frappe-ui"
import { ref } from "vue"

import { projectPage, projectTitle } from "../../projects"
import ProjectDialog from "../ProjectDialog.vue"

// the heading over a project's chatbox
defineProps<{ project: string }>()
const editing = ref(false)
</script>
