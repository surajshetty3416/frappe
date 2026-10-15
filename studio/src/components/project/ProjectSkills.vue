<template>
	<div class="flex flex-col gap-8">
		<section class="flex flex-col">
			<p v-if="!own.length" class="px-2 py-2 text-base text-ink-gray-5">No skills yet.</p>
			<ProjectRow v-for="skill in own" :key="skill.name" :title="skill.title" :subtitle="skill.description" icon="lucide-sparkles">
				<template #suffix>
					<span v-if="!skill.enabled">Off</span>
					<span v-else-if="skill.command" class="font-mono text-xs">/skill:{{ skill.command }}</span>
					<Button
						v-if="page.project.can_write"
						variant="ghost"
						icon="lucide-x"
						:tooltip="`Remove ${skill.title} from this project`"
						@click="save(own.filter((kept) => kept !== skill).map((kept) => kept.name))"
					/>
				</template>
			</ProjectRow>
		</section>

		<section v-if="everywhere.length" class="flex flex-col">
			<h2 class="flex h-9 items-center px-2 text-sm font-medium text-ink-gray-6">In every chat</h2>
			<ProjectRow v-for="skill in everywhere" :key="skill.name" :title="skill.title" :subtitle="skill.description" icon="lucide-sparkles">
				<template #suffix>
					<span v-if="skill.command" class="font-mono text-xs">/skill:{{ skill.command }}</span>
				</template>
			</ProjectRow>
		</section>
	</div>
</template>

<script setup lang="ts">
import { Button, toast } from "frappe-ui"
import { computed } from "vue"

import { type ProjectPage, errorText, setProjectSkills } from "../../projects"
import ProjectRow from "./ProjectRow.vue"

const props = defineProps<{ page: ProjectPage }>()
const emit = defineEmits<{ changed: [] }>()

const own = computed(() => props.page.skills.filter((skill) => skill.own))
const everywhere = computed(() => props.page.skills.filter((skill) => !skill.own))

async function save(skills: string[]) {
	try {
		await setProjectSkills(props.page.project.name, skills)
		emit("changed")
	} catch (error) {
		toast.error(errorText(error))
	}
}
</script>
