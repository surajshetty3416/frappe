<template>
	<div data-layer="shell" class="h-full overflow-y-auto">
		<div class="mx-auto flex w-full max-w-[960px] flex-col gap-10 px-6 pb-32 pt-12">
			<header class="flex items-start gap-4">
				<div class="mr-auto flex flex-col gap-1">
					<h1 class="text-3xl font-semibold text-ink-gray-9">{{ greeting }}</h1>
					<p class="text-base text-ink-gray-5">Open what your team built, or ask about it below.</p>
				</div>
				<Button v-if="home && !editing" variant="ghost" icon-left="lucide-layout-dashboard" label="Customize" @click="startEditing" />
			</header>

			<div v-if="!home" class="flex h-24 items-center justify-center">
				<LoadingIndicator class="size-4 text-ink-gray-5" />
			</div>

			<template v-else-if="editing">
				<p class="rounded-6 bg-surface-gray-1 px-3 py-2 text-base text-ink-gray-6">
					Move, remove or add sections. You can also ask the assistant, like “Put the registrations dashboard at the top of my home”.
				</p>
				<div
					v-for="(section, i) in draft"
					:key="section.id"
					class="rounded-8 border border-dashed border-outline-gray-3 p-4"
				>
					<HomeSection :section="section">
						<template #actions>
							<Button variant="ghost" size="sm" icon="lucide-arrow-up" tooltip="Move up" :disabled="i === 0" @click="move(i, -1)" />
							<Button variant="ghost" size="sm" icon="lucide-arrow-down" tooltip="Move down" :disabled="i === draft.length - 1" @click="move(i, 1)" />
							<Button variant="ghost" size="sm" icon="lucide-trash-2" tooltip="Remove" @click="draft.splice(i, 1)" />
						</template>
					</HomeSection>
				</div>
				<Dropdown :options="addOptions" align="start">
					<Button icon-left="lucide-plus" label="Add section" />
				</Dropdown>
				<footer class="flex flex-wrap items-center gap-2 border-t border-outline-gray-1 pt-4">
					<Button variant="solid" label="Save" :loading="saving" @click="save(false)" />
					<Button label="Cancel" @click="editing = false" />
					<span class="flex-1" />
					<Button v-if="home.customized" variant="ghost" label="Reset to default" @click="reset" />
					<Button v-if="home.can_set_default" variant="ghost" label="Save as everyone's home" @click="save(true)" />
				</footer>
			</template>

			<template v-else>
				<HomeSection v-for="section in shown" :key="section.id" :section="section" />
			</template>
		</div>
		<ViewPicker v-model:open="picking" @pick="addEmbed" />
	</div>
</template>

<script setup lang="ts">
import { Button, Dropdown, LoadingIndicator } from "frappe-ui"
import { computed, ref } from "vue"

import { artifactKinds } from "../artifacts"
import { sessionUser } from "../session"
import HomeSection from "./HomeSection.vue"
import ViewPicker from "./ViewPicker.vue"
import { type HomeArtifact, type Section, home, loadHome, openView, resetLayout, saveLayout } from "./home"

openView.value = null
document.title = "Home"
loadHome()

const firstName = decodeURIComponent(document.cookie.match(/full_name=([^;]*)/)?.[1] ?? sessionUser())
	.replace(/\+/g, " ")
	.split(" ")[0]
const greeting = computed(() => {
	const hour = new Date().getHours()
	const part = hour < 12 ? "morning" : hour < 17 ? "afternoon" : "evening"
	return `Good ${part}, ${firstName}`
})

// an empty pinned section says how to fill it only while the home is arranged
const shown = computed(() => home.value?.sections.filter((section) => section.type !== "pinned" || section.artifacts?.length) ?? [])

const editing = ref(false)
const draft = ref<Section[]>([])
const saving = ref(false)
const picking = ref(false)

function startEditing() {
	draft.value = JSON.parse(JSON.stringify(home.value?.sections ?? []))
	editing.value = true
}

function move(i: number, step: number) {
	const [section] = draft.value.splice(i, 1)
	draft.value.splice(i + step, 0, section)
}

const add = (section: Omit<Section, "id" | "title">) =>
	draft.value.push({ id: Math.random().toString(36).slice(2, 10), title: null, ...section })

const addOptions = computed(() => [
	{ label: "Pinned", icon: "lucide-pin", onClick: () => add({ type: "pinned" }) },
	{ label: "Recently updated", icon: "lucide-clock", onClick: () => add({ type: "recent" }) },
	{ label: "Browse", icon: "lucide-layout-grid", onClick: () => add({ type: "browse" }) },
	...artifactKinds.map((kind) => ({
		label: `All ${kind.title.toLowerCase()}`,
		icon: kind.icon,
		onClick: () => add({ type: "list", doctype: kind.doctypes[0] }),
	})),
	{ label: "A view, shown in the page", icon: "lucide-app-window", onClick: () => (picking.value = true) },
])

function addEmbed(artifact: HomeArtifact) {
	add({ type: "embed", doctype: artifact.doctype, name: artifact.name })
}

async function save(forEveryone: boolean) {
	saving.value = true
	try {
		await saveLayout(draft.value, forEveryone)
		editing.value = false
	} finally {
		saving.value = false
	}
}

async function reset() {
	await resetLayout()
	editing.value = false
}
</script>
