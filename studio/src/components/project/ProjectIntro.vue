<template>
	<div class="flex items-start gap-3">
		<div class="min-w-0 flex-1">
			<h1 class="text-3xl font-semibold text-ink-gray-9">What do you want to build in {{ projectTitle(project) }}?</h1>
			<p class="mt-1.5 text-p-base text-ink-gray-6">
				{{ projectPage?.project.description || "A website, a dashboard, an app, or any change to the data on this site." }}
			</p>
		</div>
		<template v-if="projectPage?.project.can_write">
			<Dropdown :options="options" align="end">
				<template #trigger>
					<Button variant="ghost" icon="lucide-ellipsis" :aria-label="`${projectPage.project.title} options`" />
				</template>
			</Dropdown>
			<ProjectDialog v-model:open="editing" :project="projectPage.project" />
		</template>
	</div>
</template>

<script setup lang="ts">
import { Button, Dropdown, dialog } from "frappe-ui"
import { ref } from "vue"
import { useRouter } from "vue-router"

import { chats } from "../../chats"
import { deleteProject, newChatRoute, projectPage, projectTitle } from "../../projects"
import ProjectDialog from "../ProjectDialog.vue"

// the heading over a project's chatbox, with the project's own actions
const props = defineProps<{ project: string }>()
const router = useRouter()
const editing = ref(false)

const options = [
	{ label: "Edit", icon: "lucide-pencil", onClick: () => (editing.value = true) },
	{ label: "Delete", icon: "lucide-trash-2", theme: "red" as const, onClick: confirmDelete },
]

function confirmDelete() {
	const count = chats.value.filter((chat) => chat.project === props.project).length
	const lost = count ? `This also deletes its ${count} ${count === 1 ? "chat" : "chats"}. ` : ""
	dialog.danger({
		title: `Delete ${projectTitle(props.project)}?`,
		message: `${lost}The apps, websites and dashboards that its chats made stay.`,
		onConfirm: async () => {
			await deleteProject(props.project)
			router.push(newChatRoute(null))
		},
	})
}
</script>
