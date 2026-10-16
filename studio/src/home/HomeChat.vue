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
					<h2 class="text-xl font-semibold text-ink-gray-9">{{ setup ? "Let's set you up" : "Ask about anything here" }}</h2>
					<p class="mt-1 text-base text-ink-gray-5">
						{{ setup ? "Tell me what you work on, and I'll build your workspace." : "Ask about your work, or change your workspace." }}
					</p>
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
import { chatSend, homeChat, kindOf, openRecord, openView, pane, question, viewInChat, viewRoute } from "./home"

const FlowApp = defineAsyncComponent(async () => {
	await import("@ai/index.css")
	return import("@ai/App.vue")
})

// in the first-run setup, every message tells the assistant so, and it leads the person through it
const props = defineProps<{ setup?: { site: boolean } }>()

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

// the view on screen, or the record open beside the workspace, rides along with each message, unless the person took it off
function attached(): ChatContext["artifact"] | null {
	if (!viewInChat.value) return null
	const view = openView.value
	if (view) return { doctype: view.doctype, name: view.name, title: view.title, path: view.route }
	const record = pane.value.open && pane.value.tab === "record" ? openRecord.value : null
	return record ? { doctype: record.doctype, name: record.name, title: record.title ?? record.name, path: "/home" } : null
}
const context = {
	snapshot: () => {
		const artifact = attached()
		const snapshot = { ...(artifact ? { artifact } : {}), ...(props.setup ? { setup: props.setup } : {}) }
		return Object.keys(snapshot).length ? snapshot : null
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
