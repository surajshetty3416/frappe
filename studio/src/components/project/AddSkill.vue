<template>
	<Dropdown :options="options" align="end">
		<template #trigger><Button variant="subtle" icon-left="lucide-plus" label="Add skill" /></template>
	</Dropdown>
	<SkillDialog v-model:open="creating" @created="(skill: string) => add(skill)" />
</template>

<script setup lang="ts">
import { Button, Dropdown, call, toast } from "frappe-ui"
import { computed, onMounted, ref } from "vue"

import { type ProjectPage, errorText, setProjectSkills } from "../../projects"
import SkillDialog from "./SkillDialog.vue"

// one of the site's other skills, or a new one, for the project's chats
const props = defineProps<{ page: ProjectPage }>()
const emit = defineEmits<{ changed: [] }>()
const creating = ref(false)

const others = ref<{ name: string; title: string }[]>([])
onMounted(async () => {
	others.value = await call<{ name: string; title: string }[]>("frappe.client.get_list", {
		doctype: "Flow Skill",
		filters: { enabled: 1, is_global: 0 },
		fields: ["name", "title"],
		order_by: "title asc",
		limit_page_length: 0,
	}).catch(() => [])
})

const options = computed(() => {
	const addable = others.value.filter((skill) => !props.page.skills.some((listed) => listed.name === skill.name))
	const create = { label: "New skill", icon: "lucide-pen-line", onClick: () => (creating.value = true) }
	if (!addable.length) return [create]
	return [
		{ group: "Skills", hideLabel: true, options: addable.map((skill) => ({ label: skill.title, onClick: () => add(skill.name) })) },
		{ group: "New", hideLabel: true, options: [create] },
	]
})

async function add(skill: string) {
	const own = props.page.skills.filter((listed) => listed.own).map((listed) => listed.name)
	try {
		await setProjectSkills(props.page.project.name, [...own, skill])
		emit("changed")
	} catch (error) {
		toast.error(errorText(error))
	}
}
</script>
