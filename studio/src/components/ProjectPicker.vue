<template>
	<Dropdown :options="options" align="start">
		<template #trigger>
			<slot :title="selectedTitle">
				<Button variant="subtle" icon-right="lucide-chevron-down" :label="selectedTitle" />
			</slot>
		</template>
	</Dropdown>
	<ProjectDialog v-if="canCreate" v-model:open="creating" />
</template>

<script setup lang="ts">
import { Button, Dropdown } from "frappe-ui"
import { computed, ref } from "vue"

import { projectTitle, projects } from "../projects"
import ProjectDialog from "./ProjectDialog.vue"

// picks one of the person's projects; with `allLabel`, none stands for all of them, and with
// `canCreate` a new one opens once made
const props = defineProps<{ allLabel?: string; canCreate?: boolean }>()
const creating = ref(false)
const selected = defineModel<string | null>({ required: true })

const selectedTitle = computed(() => (selected.value ? projectTitle(selected.value) : props.allLabel ?? "Pick a project"))
const options = computed(() => [
	{ group: "Projects", hideLabel: true, options: choices.value },
	...(props.canCreate
		? [{ group: "New", hideLabel: true, options: [{ label: "New project", icon: "lucide-plus", onClick: () => (creating.value = true) }] }]
		: []),
])
const choices = computed(() => [
	...(props.allLabel
		? [{ label: props.allLabel, icon: "lucide-layers", selected: !selected.value, onClick: () => (selected.value = null) }]
		: []),
	...projects.value.map((project) => ({
		label: project.title,
		icon: "lucide-folder",
		selected: project.name === selected.value,
		onClick: () => (selected.value = project.name),
	})),
])
</script>
