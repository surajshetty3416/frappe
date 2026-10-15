<template>
	<Dialog
		v-model:open="open"
		:title="project ? 'Edit project' : 'New project'"
		size="md"
		:actions="[
			{ label: 'Cancel', variant: 'ghost' },
			{ label: project ? 'Save' : 'Create project', variant: 'solid', disabled: !title.trim(), onClick: save },
		]"
	>
		<form data-layer="shell" class="flex flex-col gap-4" @submit.prevent="title.trim() && save()">
			<FormControl v-model="title" label="Name" placeholder="Frappeverse 2027" autofocus />
			<FormControl
				v-model="description"
				type="textarea"
				label="What is it for?"
				placeholder="The conference: its data, website, badges and emails"
				:rows="2"
			/>
		</form>
	</Dialog>
</template>

<script setup lang="ts">
import { Dialog, FormControl, toast } from "frappe-ui"
import { ref, watch } from "vue"
import { useRouter } from "vue-router"

import { type Project, createProject, errorText, projectRoute, updateProject } from "../projects"

// a new project, or the name and purpose of `project`
const props = defineProps<{ project?: Pick<Project, "name" | "title" | "description"> | null }>()
const open = defineModel<boolean>("open", { required: true })
const router = useRouter()
const title = ref("")
const description = ref("")

watch(
	open,
	(opened) => {
		if (!opened) return
		title.value = props.project?.title ?? ""
		description.value = props.project?.description ?? ""
	},
	{ immediate: true }
)

async function save() {
	const values = { title: title.value.trim(), description: description.value.trim() }
	try {
		if (props.project) await updateProject(props.project.name, values)
		else router.push(projectRoute(await createProject(values.title, values.description)))
		open.value = false
	} catch (error) {
		toast.error(errorText(error))
	}
}
</script>
