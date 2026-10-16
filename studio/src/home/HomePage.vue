<template>
	<div data-layer="shell" class="h-full overflow-y-auto">
		<div class="mx-auto flex w-full max-w-[1280px] flex-col gap-6 px-6 pb-32 pt-8">
			<header class="flex flex-wrap items-center gap-2">
				<div class="mr-auto flex flex-col gap-0.5">
					<h1 class="text-2xl font-semibold text-ink-gray-9">{{ greeting }}</h1>
					<p class="text-base text-ink-gray-5">{{ today }}</p>
				</div>
				<template v-if="workspace && !editing">
					<Button variant="ghost" icon-left="lucide-sparkles" label="Improve with AI" @click="improve" />
					<Button variant="ghost" icon-left="lucide-layout-dashboard" label="Arrange" @click="startEditing" />
				</template>
				<template v-if="editing">
					<Button v-if="workspace?.customized" variant="ghost" label="Reset" @click="reset" />
					<Button v-if="workspace?.can_set_default" variant="ghost" label="Save for everyone" @click="save(true)" />
					<Button label="Cancel" @click="editing = false" />
					<Button variant="solid" label="Save" :loading="saving" @click="save(false)" />
				</template>
			</header>

			<div v-if="!workspace" class="flex h-24 items-center justify-center">
				<LoadingIndicator class="size-4 text-ink-gray-5" />
			</div>
			<template v-else>
				<p v-if="editing" class="rounded-6 bg-surface-gray-1 px-3 py-2 text-base text-ink-gray-6">
					Move, resize or remove widgets. To add one, describe it to the assistant, like “a queue of sponsors who haven't replied”.
				</p>
				<WorkspaceGrid :widgets="editing ? draft : workspace.widgets" :editing="editing" @update="(widgets) => (draft = widgets)" />
				<button
					v-if="!editing"
					type="button"
					class="flex items-center justify-center gap-2 rounded-8 border border-dashed border-outline-gray-2 py-4 text-base text-ink-gray-5 hover:border-outline-gray-3 hover:text-ink-gray-7"
					@click="addWidget"
				>
					<span class="lucide-plus size-4" />Add a widget by describing it
				</button>
			</template>
		</div>
	</div>
</template>

<script setup lang="ts">
import { Button, LoadingIndicator, dayjs } from "frappe-ui"
import { computed, ref } from "vue"

import { sessionUser } from "../session"
import WorkspaceGrid from "./WorkspaceGrid.vue"
import { type Widget, ask, askFocus, loadWorkspace, openView, resetWorkspace, saveWorkspace, workspace } from "./home"

openView.value = null
document.title = "Home"
loadWorkspace()

const firstName = decodeURIComponent(document.cookie.match(/full_name=([^;]*)/)?.[1] ?? sessionUser())
	.replace(/\+/g, " ")
	.split(" ")[0]
const greeting = computed(() => {
	const hour = new Date().getHours()
	const part = hour < 12 ? "morning" : hour < 17 ? "afternoon" : "evening"
	return `Good ${part}, ${firstName}`
})
const today = dayjs().format("dddd, D MMMM")

const editing = ref(false)
const draft = ref<Widget[]>([])
const saving = ref(false)

function startEditing() {
	draft.value = JSON.parse(JSON.stringify(workspace.value?.widgets ?? []))
	editing.value = true
}

async function save(forEveryone: boolean) {
	saving.value = true
	try {
		await saveWorkspace(draft.value, forEveryone)
		editing.value = false
	} finally {
		saving.value = false
	}
}

async function reset() {
	await resetWorkspace()
	editing.value = false
}

const addWidget = () => askFocus.value++

const improve = () =>
	ask(
		"Look at how I've been working lately (what I changed, what's assigned to me, what waits on me) and at my workspace. " +
			"Suggest what to add, change or drop so I can do more from here. Ask me before you change it."
	)
</script>
