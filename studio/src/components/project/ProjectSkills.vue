<template>
	<div class="flex flex-col gap-8">
		<section class="flex flex-col">
			<div class="flex h-9 items-center gap-2 px-2">
				<h2 class="flex-1 text-sm font-medium text-ink-gray-6">This project's skills</h2>
				<template v-if="page.project.can_write">
					<Dropdown v-if="addable.length" :options="addable" align="end">
						<template #trigger><Button variant="subtle" size="sm" icon-left="lucide-plus" label="Add skill" /></template>
					</Dropdown>
					<Button variant="subtle" size="sm" icon-left="lucide-pen-line" label="New skill" @click="creating = true" />
				</template>
			</div>
			<ProjectEmpty
				v-if="!own.length"
				title="No skills of its own"
				text="A skill is a set of instructions a chat loads when a task calls for it: a house style, a checklist, how to name things. Skills added here reach every new chat in this project."
			/>
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
		<SkillDialog v-model:open="creating" @created="(skill) => save([...own.map((kept) => kept.name), skill])" />
	</div>
</template>

<script setup lang="ts">
import { Button, Dropdown, call, toast } from "frappe-ui"
import { computed, onMounted, ref } from "vue"

import { type ProjectPage, errorText, updateProject } from "../../projects"
import ProjectEmpty from "./ProjectEmpty.vue"
import ProjectRow from "./ProjectRow.vue"
import SkillDialog from "./SkillDialog.vue"

const props = defineProps<{ page: ProjectPage }>()
const emit = defineEmits<{ changed: [] }>()

const own = computed(() => props.page.skills.filter((skill) => skill.own))
const everywhere = computed(() => props.page.skills.filter((skill) => !skill.own))
const creating = ref(false)

// the site's other skills, which the project can take on
const others = ref<{ name: string; title: string }[]>([])
onMounted(async () => {
	if (!props.page.project.can_write) return
	others.value = await call<{ name: string; title: string }[]>("frappe.client.get_list", {
		doctype: "Flow Skill",
		filters: { enabled: 1, is_global: 0 },
		fields: ["name", "title"],
		order_by: "title asc",
		limit_page_length: 0,
	}).catch(() => [])
})
const addable = computed(() =>
	others.value
		.filter((skill) => !props.page.skills.some((listed) => listed.name === skill.name))
		.map((skill) => ({ label: skill.title, onClick: () => save([...own.value.map((kept) => kept.name), skill.name]) }))
)

async function save(skills: string[]) {
	try {
		await updateProject(props.page.project.name, { skills: skills.map((skill) => ({ skill })) })
		emit("changed")
	} catch (error) {
		toast.error(errorText(error))
	}
}
</script>
