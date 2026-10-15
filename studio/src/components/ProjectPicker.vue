<template>
	<Dropdown :options="options" align="start">
		<template #trigger>
			<slot :title="selectedTitle">
				<Button variant="subtle" icon-right="lucide-chevron-down" :label="selectedTitle" />
			</slot>
		</template>
	</Dropdown>
</template>

<script setup lang="ts">
import { Button, Dropdown } from "frappe-ui"
import { computed } from "vue"

import { projectTitle, projects } from "../projects"

// picks one of the person's projects; with `allLabel`, none stands for all of them
const props = defineProps<{ allLabel?: string }>()
const selected = defineModel<string | null>({ required: true })

const selectedTitle = computed(() => (selected.value ? projectTitle(selected.value) : props.allLabel ?? "Pick a project"))
const options = computed(() => [
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
