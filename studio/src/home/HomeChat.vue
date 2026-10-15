<template>
	<div data-layer="ai" class="flex h-full w-full flex-col bg-surface-base">
		<FlowApp
			ref="flowApp"
			:session="homeChat"
			:initial-message="question"
			:context="context"
			:artifact-icon="artifactIcon"
			@session="onSession"
			@artifact="onArtifact"
		>
			<template #intro>
				<div data-layer="shell" class="px-2 text-center">
					<h2 class="text-xl font-semibold text-ink-gray-9">Ask about anything here</h2>
					<p class="mt-1 text-base text-ink-gray-5">Find a view, or ask a question of the one you have open.</p>
				</div>
			</template>
		</FlowApp>
	</div>
</template>

<script setup lang="ts">
import { defineAsyncComponent, onBeforeUnmount, ref } from "vue"
import { useRouter } from "vue-router"

import { type Artifact, artifactIcon } from "../artifacts"
import { type ChatContext, contextChips } from "../context"
import { chatSend, homeChat, kindOf, openView, question, viewInChat, viewRoute } from "./home"

const FlowApp = defineAsyncComponent(async () => {
	await import("@ai/index.css")
	return import("@ai/App.vue")
})

const router = useRouter()

const flowApp = ref<{ send: (message: string) => boolean } | null>(null)
chatSend.value = (message) => flowApp.value?.send(message) ?? false
onBeforeUnmount(() => (chatSend.value = null))

function onSession(session: string | null) {
	homeChat.value = session
	question.value = ""
}

// what the chat makes or names opens where a reader uses it, or in Studio when the home cannot show it
function onArtifact(artifact: Artifact) {
	router.push(kindOf(artifact.doctype) ? viewRoute(artifact) : artifact.route)
}

// the view on screen rides along with each message, unless the person took it off
function attached(): ChatContext["artifact"] | null {
	const view = openView.value
	if (!view || !viewInChat.value) return null
	return { doctype: view.doctype, name: view.name, title: view.title, path: view.route }
}
const context = {
	snapshot: () => {
		const artifact = attached()
		return artifact ? { artifact } : null
	},
	sent: () => {},
	pending: () => [],
	attached: () => {
		const artifact = attached()
		return artifact ? contextChips({ artifact }) : []
	},
	remove: () => (viewInChat.value = false),
	pick: () => (viewInChat.value = true),
	chips: contextChips,
}
</script>
