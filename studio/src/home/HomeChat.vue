<template>
	<div data-layer="ai" class="flex h-full w-full flex-col bg-surface-base">
		<FlowApp
			ref="flowApp"
			:session="homeChat"
			:initial-message="question"
			:context="context"
			:artifact-icon="artifactIcon"
			:orchestrate="false"
			:intro-at-top="Boolean(setup)"
			:placeholder="setup ? 'Tell me about your organization…' : 'Ask about your work…'"
			@session="onSession"
			@artifact="onArtifact"
		>
			<template #intro>
				<div data-layer="shell" class="px-2" :class="setup ? '' : 'text-center'">
					<h2 class="text-base font-semibold text-ink-gray-9">{{ setup ? "Describe it instead" : "Ask about anything here" }}</h2>
					<p class="mt-1 text-sm text-ink-gray-5">
						{{
							setup
								? "Tell me what your organization does and who works on what. I'll fill in the steps and set up the Spaces."
								: "Ask about your work, or change your workspace."
						}}
					</p>
				</div>
			</template>
			<template v-if="setup" #starters="{ prefill }">
				<div data-layer="shell" class="flex flex-col items-start gap-1 px-1 pt-2">
					<button
						v-for="idea in SETUP_IDEAS"
						:key="idea"
						type="button"
						class="rounded-4 px-2 py-1 text-left text-sm text-ink-gray-6 hover:bg-surface-gray-2 hover:text-ink-gray-8"
						@click="prefill(idea)"
					>
						{{ idea }}
					</button>
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
import { chatSend, homeChat, kindOf, openRecord, openSpace, openView, pane, question, viewInChat, viewRoute } from "./home"

const FlowApp = defineAsyncComponent(async () => {
	await import("@ai/index.css")
	return import("@ai/App.vue")
})

// in the first-run setup, every message tells the assistant so, and it leads the person through it
const props = defineProps<{ setup?: { site: boolean } }>()

const SETUP_IDEAS = [
	"We're a software company of about 70 people in Mumbai.",
	"Support and partnerships are our busiest teams.",
	"Set up a Space for our events team.",
]

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

// the view on screen, the record open beside the workspace, or the Space open, rides along with each message, unless the person took it off
function attached(): ChatContext["artifact"] | null {
	if (!viewInChat.value) return null
	const view = openView.value
	if (view) return { doctype: view.doctype, name: view.name, title: view.title, path: view.route }
	const record = pane.value.open && pane.value.tab === "record" ? openRecord.value : null
	if (record) return { doctype: record.doctype, name: record.name, title: record.title ?? record.name, path: "/home" }
	const space = openSpace.value
	return space ? { doctype: "Workspace", name: space.name, title: space.title, path: `/home/s/${encodeURIComponent(space.name)}` } : null
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
