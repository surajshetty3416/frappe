<template>
	<!-- the menu sits at the edge, so the question stays centered over the chatbox -->
	<div class="relative">
		<h1 class="px-10 text-center text-3xl font-semibold text-ink-gray-9">What do you want to build in {{ projectTitle(project) }}?</h1>
		<template v-if="projectPage?.project.can_write">
			<div class="absolute right-0 top-0">
				<Dropdown :options="options" align="end">
					<template #trigger>
						<Button variant="ghost" icon="lucide-ellipsis" :aria-label="`${projectPage.project.title} options`" />
					</template>
				</Dropdown>
			</div>
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
