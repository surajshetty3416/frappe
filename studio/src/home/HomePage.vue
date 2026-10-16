<template>
	<div data-layer="shell" class="h-full overflow-y-auto">
		<div class="mx-auto flex w-full max-w-[1600px] flex-col gap-3 px-5 pb-28 pt-4">
			<header class="flex h-9 flex-wrap items-center gap-2">
				<h1 class="text-lg font-semibold text-ink-gray-9">{{ greeting }}</h1>
				<span class="mr-auto text-sm text-ink-gray-5">{{ today }}</span>
				<template v-if="workspace && !editing">
					<Button variant="ghost" size="sm" icon-left="lucide-sparkles" label="Improve with AI" @click="improve" />
					<Button variant="ghost" size="sm" icon-left="lucide-layout-dashboard" label="Arrange" @click="startEditing" />
				</template>
				<template v-if="editing">
					<Button v-if="workspace?.customized" variant="ghost" size="sm" label="Reset" @click="reset" />
					<Button v-if="workspace?.can_set_default" variant="ghost" size="sm" label="Save for everyone" @click="save(true)" />
					<Button size="sm" label="Cancel" @click="editing = false" />
					<Button variant="solid" size="sm" label="Save" :loading="saving" @click="save(false)" />
				</template>
			</header>

			<div v-if="!workspace" class="flex h-24 items-center justify-center">
				<LoadingIndicator class="size-4 text-ink-gray-5" />
			</div>
			<template v-else>
				<!-- once, for someone new: their Home is already set up from their Spaces -->
				<section v-if="workspace.setup.welcome && !editing" class="flex items-start gap-4 rounded-3 border border-outline-gray-2 p-4">
					<span class="lucide-sparkles mt-0.5 size-4 shrink-0 text-ink-gray-6" />
					<div class="min-w-0 flex-1">
						<p class="text-sm font-medium text-ink-gray-8">Welcome{{ workspace.organization ? ` to ${workspace.organization}` : "" }}, {{ firstName }}</p>
						<p class="mt-0.5 text-sm text-ink-gray-6">
							This is your Home: what waits on you from each of your Spaces, ready to work in. Your Spaces are on the left; open one to see
							what your team is doing. Ask anything with ⌘K.
						</p>
						<div class="mt-3 flex gap-2">
							<Button size="sm" variant="solid" label="Got it" @click="dismissWelcome" />
							<Button size="sm" variant="ghost" icon-left="lucide-sparkles" label="Tailor my Home with the assistant" @click="tailor" />
						</div>
					</div>
				</section>
				<p v-if="editing" class="text-sm text-ink-gray-5">
					Move, resize or remove your own widgets. Widgets from your Spaces are arranged in each Space. To add one, describe it to the
					assistant, like “a queue of sponsors who haven't replied”.
				</p>
				<WorkspaceGrid :widgets="editing ? draft : workspace.widgets" :editing="editing" @update="(widgets) => (draft = widgets)" />
				<button
					v-if="!editing"
					type="button"
					class="flex h-9 items-center justify-center gap-2 rounded-3 border border-dashed border-outline-gray-2 text-sm text-ink-gray-5 hover:border-outline-gray-3 hover:text-ink-gray-7"
					@click="addWidget"
				>
					<span class="lucide-plus size-3.5" />Add a widget by describing it<kbd class="ml-1 font-mono text-xs text-ink-gray-4">⌘K</kbd>
				</button>
			</template>
		</div>
	</div>
</template>

<script setup lang="ts">
import { Button, LoadingIndicator, call, dayjs } from "frappe-ui"
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
const today = dayjs().format("ddd, D MMM")

const editing = ref(false)
const draft = ref<Widget[]>([])
const saving = ref(false)

// only the person's own widgets; the Spaces' slices are each Space's to arrange
function startEditing() {
	draft.value = JSON.parse(JSON.stringify(workspace.value?.widgets.filter((widget) => !widget.space) ?? []))
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

async function dismissWelcome() {
	await call("frappe.ai.workspace.dismiss_welcome")
	await loadWorkspace()
}

function tailor() {
	dismissWelcome()
	ask("Ask me what I work on day to day, then tailor my Home to it. Ask before you change it.")
}

const improve = () =>
	ask(
		"Look at how I've been working lately (what I changed, what's assigned to me, what waits on me) and at my workspace. " +
			"Suggest what to add, change or drop so I can do more from here. Ask me before you change it."
	)
</script>
