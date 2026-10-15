<template>
	<div data-layer="ai" class="flex h-full w-full flex-col bg-surface-base">
		<FlowApp
			v-if="ready"
			ref="flowApp"
			:session="current"
			:project="activeProject"
			:initial-message="initialMessage"
			:context="context"
			:artifact-icon="artifactIcon"
			:intro-at-top="onProject"
			@session="onSession"
			@artifact="onArtifact"
		>
			<template #intro>
				<div data-layer="shell" class="mx-auto w-full max-w-[760px]">
					<template v-if="artifact">
						<h1 class="text-3xl font-semibold text-ink-gray-9">What should change?</h1>
						<p class="mt-1.5 text-p-base text-ink-gray-6">Ask for any change to {{ openTitle }}, or comment on its preview.</p>
					</template>
					<ProjectIntro v-else-if="onProject && activeProject" :project="activeProject" />
					<template v-else>
						<h1 class="text-3xl font-semibold text-ink-gray-9">
							What do you want to build<template v-if="activeProject">
								in
								<!-- the home's new chat can still move to another project -->
								<ProjectPicker v-if="route.name === 'studio-home'" :model-value="activeProject" @update:model-value="moveTo">
									<template #default="{ title }">
										<button
											type="button"
											class="rounded-4 underline decoration-outline-gray-3 decoration-2 underline-offset-[6px] hover:decoration-outline-gray-4"
										>{{ title }}</button>
									</template>
								</ProjectPicker>
								<template v-else>{{ projectTitle(activeProject) }}</template>
							</template>?
						</h1>
						<p class="mt-1.5 text-p-base text-ink-gray-6">A website, a dashboard, an app, or any change to the data on this site.</p>
					</template>
					<Alert
						v-if="needsSetup"
						class="mt-4"
						theme="amber"
						title="Studio needs an AI model before it can answer."
						:primary-action="{ label: 'Set up a model', onClick: () => router.push('/studio/settings/model') }"
					/>
				</div>
			</template>
			<template #starters="{ prefill }">
				<div v-if="onProject && activeProject" data-layer="shell" class="mx-auto w-full max-w-[760px]">
					<ProjectHome :project="activeProject" @prefill="prefill" />
				</div>
				<div v-else data-layer="shell" class="mx-auto w-full max-w-[760px]">
					<div class="flex flex-wrap gap-1.5">
						<!-- a starter that waits for the rest of the sentence trails off -->
						<Button v-for="idea in ideas" :key="idea.text" variant="outline" :icon-left="idea.icon" @click="prefill(idea.text)">
							{{ idea.text.trim() }}<span v-if="idea.text.endsWith(' ')" class="text-ink-gray-4">…</span>
						</Button>
					</div>
					<RecordingList v-if="!artifact" :project="activeProject" class="mt-8" />
				</div>
			</template>
		</FlowApp>
		<div v-else class="flex flex-1 items-center justify-center">
			<LoadingIndicator class="size-4 text-ink-gray-5" />
		</div>
	</div>
</template>

<script setup lang="ts">
import { Alert, Button, LoadingIndicator } from "frappe-ui"
import { computed, defineAsyncComponent, onBeforeUnmount, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"

import { type Artifact, artifactIcon, getArtifactSession, linkArtifact, routeArtifact } from "../artifacts"
import { activeProject, newChatRoute, projectRoute, projectTitle } from "../projects"
import { attachedChips, chatContext, clearSent, contextChips, detach, pendingChips, pick } from "../context"
import { chatSender } from "../editor"
import { findTab } from "../tabs"
import ProjectPicker from "./ProjectPicker.vue"
import ProjectHome from "./project/ProjectHome.vue"
import ProjectIntro from "./project/ProjectIntro.vue"
import RecordingList from "./RecordingList.vue"

const route = useRoute()
const router = useRouter()

const FlowApp = defineAsyncComponent(async () => {
	await import("@ai/index.css")
	return import("@ai/App.vue")
})

// the home and a project's page are each a new chat
const onProject = computed(() => route.name === "studio-project")
const onChatRoute = computed(() => route.name === "studio-chat" || route.name === "studio-home" || onProject.value)
// the artifact the editor beside the chat has open
const artifact = computed(() => routeArtifact(route))
const routeSession = computed(() => {
	const session = onChatRoute.value ? route.params.session : route.query.chat
	return typeof session === "string" && session !== "new" ? session : null
})

// the chat on screen; the chat keeps every chat it opened running, and shows this one
const current = ref<string | null>(null)
const ready = ref(false)
const initialMessage = ref("")

async function resolve() {
	let wanted = routeSession.value
	if (!wanted && artifact.value && !onChatRoute.value) {
		wanted = (await getArtifactSession(artifact.value.doctype, artifact.value.name))?.name ?? null
	}
	// the chat that built the artifact is the open chat, for the top bar and the sidebar too
	if (wanted && !routeSession.value && !onChatRoute.value) router.replace({ query: { ...route.query, chat: wanted } })
	initialMessage.value = onChatRoute.value && typeof route.query.prompt === "string" ? route.query.prompt : ""
	current.value = wanted
	ready.value = true
}
watch(() => [routeSession.value, artifact.value?.doctype, artifact.value?.name], resolve, { immediate: true })

function onSession(session: string | null) {
	if (session === current.value) return
	// the open chat was deleted
	if (!session) return router.push(activeProject.value ? projectRoute(activeProject.value) : newChatRoute(null))
	current.value = session
	if (onChatRoute.value) {
		router.replace({ name: "studio-chat", params: { session } })
		return
	}
	if (artifact.value) linkArtifact(session, artifact.value.doctype, artifact.value.name)
	router.replace({ query: { ...route.query, chat: session } })
}

function onArtifact(made: Artifact) {
	if (route.path === made.route) return
	router.push({ path: made.route, query: current.value ? { chat: current.value } : {} })
}

// an editor action that asks the agent sends through the open chat
const flowApp = ref<{ send: (message: string) => boolean } | null>(null)
chatSender.value = (message) => flowApp.value?.send(message) ?? false
onBeforeUnmount(() => (chatSender.value = null))

const needsSetup = !window.flow_boot?.models?.length
const openTitle = computed(() => (artifact.value && findTab(artifact.value.doctype, artifact.value.name)?.title) || "this artifact")
const ideas = computed(() => {
	const layer = route.matched[0]?.meta.layer
	if (!artifact.value) return IDEAS
	return (typeof layer === "string" && CHANGES[layer]) || []
})

const moveTo = (project: string | null) => router.replace(newChatRoute(project))

// the editor beside the chat, so "this page" or "these" in a message has a referent
function openArtifact() {
	const open = artifact.value
	const title = open ? findTab(open.doctype, open.name)?.title || open.name : ""
	return open ? { doctype: open.doctype, name: open.name, title, path: route.path } : null
}
const context = {
	snapshot: () => chatContext(openArtifact()),
	sent: clearSent,
	pending: pendingChips,
	attached: () => attachedChips(openArtifact()),
	remove: (key: string) => detach(key, openArtifact()),
	pick: (key: string) => pick(key, openArtifact()),
	chips: contextChips,
}
</script>

<script lang="ts">
const IDEAS = [
	{ icon: "lucide-database", text: "A DocType for sponsors" },
	{ icon: "lucide-blocks", text: "An app to check in attendees" },
	{ icon: "lucide-globe", text: "A website for our conference" },
	{ icon: "lucide-chart-column", text: "A dashboard of registrations" },
	{ icon: "lucide-printer", text: "Make an attendee badge with a QR code" },
	{ icon: "lucide-mail", text: "Make a confirmation email for new registrations" },
]

// what a person usually asks of an artifact open beside the chat, by layer
const CHANGES: Record<string, { icon: string; text: string }[]> = {
	data: [
		{ icon: "lucide-plus", text: "Add a field for " },
		{ icon: "lucide-table", text: "Add demo records" },
		{ icon: "lucide-shield", text: "Let this role " },
	],
	web: [
		{ icon: "lucide-type", text: "Rewrite the copy to " },
		{ icon: "lucide-plus", text: "Add a section about " },
		{ icon: "lucide-palette", text: "Restyle the page to " },
	],
	analytics: [
		{ icon: "lucide-chart-column", text: "Add a chart of " },
		{ icon: "lucide-funnel", text: "Filter it by " },
	],
	ui: [
		{ icon: "lucide-plus", text: "Add a page to " },
		{ icon: "lucide-text-cursor-input", text: "Add a form for " },
	],
	print: [
		{ icon: "lucide-qr-code", text: "Add a QR code of " },
		{ icon: "lucide-file", text: "Change the page size to " },
		{ icon: "lucide-palette", text: "Restyle it to " },
	],
	email: [
		{ icon: "lucide-heading", text: "Change the subject to " },
		{ icon: "lucide-panel-bottom", text: "Add a footer with " },
		{ icon: "lucide-type", text: "Rewrite the message to " },
	],
	agents: [
		{ icon: "lucide-wrench", text: "Let it " },
		{ icon: "lucide-pencil", text: "Change it to " },
	],
}
</script>
