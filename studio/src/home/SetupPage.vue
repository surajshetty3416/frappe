<template>
	<div data-layer="shell" class="flex h-full min-h-0">
		<div class="flex h-full w-[460px] shrink-0 flex-col border-r border-outline-gray-1">
			<header class="flex h-12 shrink-0 items-center gap-2 border-b border-outline-gray-1 px-4">
				<span class="lucide-sparkles size-4 text-ink-gray-6" />
				<h1 class="text-base font-medium text-ink-gray-8">{{ workspace?.setup.site ? "Set up your organization" : "Set up your workspace" }}</h1>
			</header>
			<div class="min-h-0 flex-1">
				<HomeChat v-if="workspace" :setup="{ site: workspace.setup.site }" />
			</div>
		</div>
		<div class="flex min-w-0 flex-1 flex-col bg-surface-gray-1">
			<header class="flex h-12 shrink-0 items-center gap-2 border-b border-outline-gray-1 bg-surface-base px-4">
				<h2 class="mr-auto text-base font-medium text-ink-gray-8">Your workspace</h2>
				<span class="text-sm text-ink-gray-5">It fills in as you talk.</span>
				<Button variant="solid" label="Open my workspace" :loading="finishing" @click="finish" />
			</header>
			<div class="min-h-0 flex-1 overflow-y-auto p-6">
				<WorkspaceGrid v-if="workspace" :widgets="workspace.widgets" />
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { useIntervalFn } from "@vueuse/core"
import { Button, call } from "frappe-ui"
import { ref, watch } from "vue"
import { useRouter } from "vue-router"

import HomeChat from "./HomeChat.vue"
import WorkspaceGrid from "./WorkspaceGrid.vue"
import { homeChat, loadWorkspace, pane, question, workspace } from "./home"

const router = useRouter()
document.title = "Set up"

// the pane's chat is this one, here; the assistant speaks first, and a reload picks the same conversation up
pane.value.open = false
watch(homeChat, (session) => {
	if (session && session !== workspace.value?.setup.chat) call("frappe.ai.workspace.keep_setup_chat", { session })
})
loadWorkspace().then(() => {
	const setup = workspace.value?.setup
	if (setup?.chat) homeChat.value = setup.chat
	else if (!homeChat.value) question.value = setup?.site ? "Hi! Let's set up our site." : "Hi! I'm new here. Set me up."
})

// the assistant arranges the workspace from the chat; it shows here as it does
useIntervalFn(loadWorkspace, 3000)

const finishing = ref(false)
async function finish() {
	finishing.value = true
	await call("frappe.ai.workspace.finish_setup")
	await loadWorkspace()
	router.push("/home")
}
</script>
