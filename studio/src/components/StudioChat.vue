<template>
	<div data-layer="ai" class="flex h-full w-full flex-col bg-surface-base">
		<FlowApp
			v-if="ready"
			ref="flowApp"
			:session="current"
			:initial-message="initialMessage"
			:context="context"
			:artifact-icon="artifactIcon"
			@session="onSession"
			@artifact="onArtifact"
		>
			<template #intro>
				<div data-layer="shell" class="mx-auto w-full max-w-[760px]">
					<template v-if="artifact">
						<h1 class="text-3xl font-semibold text-ink-gray-9">What should change?</h1>
						<p class="mt-1.5 text-p-base text-ink-gray-6">Ask for any change to {{ openTitle }}, or comment on its preview.</p>
					</template>
					<template v-else>
						<h1 class="text-3xl font-semibold text-ink-gray-9">What do you want to build?</h1>
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
				<div data-layer="shell" class="mx-auto w-full max-w-[760px]">
					<div class="flex flex-wrap gap-1.5">
						<!-- a starter that waits for the rest of the sentence trails off -->
						<Button v-for="idea in ideas" :key="idea.text" variant="outline" :icon-left="idea.icon" @click="prefill(idea.text)">
							{{ idea.text.trim() }}<span v-if="idea.text.endsWith(' ')" class="text-ink-gray-4">…</span>
						</Button>
					</div>
					<RecordingList v-if="!artifact" class="mt-8" />
					<section v-if="recent.length && !artifact" class="mt-8">
						<h2 class="px-2 text-sm font-medium text-ink-gray-5">Recent</h2>
						<router-link
							v-for="item in recent"
							:key="item.key"
							:to="{ path: item.route, query: { chat: item.chat } }"
							class="mt-1 flex h-9 items-center gap-2 rounded-4 px-2 hover:bg-surface-gray-2"
						>
							<span :class="item.icon" class="size-4 shrink-0 text-ink-gray-5" />
							<span class="min-w-0 flex-1 truncate text-base text-ink-gray-8">{{ item.title }}</span>
							<span class="shrink-0 text-sm text-ink-gray-5">{{ item.label }}</span>
							<span class="w-28 shrink-0 whitespace-nowrap text-right text-sm text-ink-gray-4">{{ dayjs(item.modified).fromNow() }}</span>
						</router-link>
					</section>
				</div>
			</template>
		</FlowApp>
		<div v-else class="flex flex-1 items-center justify-center">
			<LoadingIndicator class="size-4 text-ink-gray-5" />
		</div>
	</div>
</template>

<script setup lang="ts">
import { Alert, Button, LoadingIndicator, dayjs } from "frappe-ui"
import { computed, defineAsyncComponent, onBeforeUnmount, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"

import { type Artifact, artifactIcon, artifactLabel, getArtifactSession, linkArtifact, routeArtifact } from "../artifacts"
import { chats } from "../chats"
import { attachedChips, chatContext, clearSent, contextChips, detach, pendingChips } from "../context"
import { chatSender } from "../editor"
import { findTab } from "../tabs"
import RecordingList from "./RecordingList.vue"

const route = useRoute()
const router = useRouter()

const FlowApp = defineAsyncComponent(async () => {
	await import("@ai/index.css")
	return import("@ai/App.vue")
})

const onChatRoute = computed(() => route.name === "studio-chat")
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
	if (!session) return router.push("/studio")
	current.value = session
	if (onChatRoute.value || route.name === "studio-home") {
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
	return (artifact.value && typeof layer === "string" && CHANGES[layer]) || IDEAS
})

// a new chat starts from the artifacts the latest chats made
const recent = computed(() => {
	const seen = new Map<string, { key: string; title: string; icon: string; label: string; route: string; chat: string; modified: string }>()
	for (const chat of chats.value)
		for (const made of chat.artifacts) {
			const key = `${made.doctype}/${made.name}`
			if (!seen.has(key))
				seen.set(key, {
					key,
					title: made.title,
					icon: artifactIcon(made),
					label: artifactLabel(made.doctype),
					route: made.route,
					chat: chat.name,
					modified: chat.modified,
				})
		}
	return [...seen.values()].slice(0, 6)
})

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
	chips: contextChips,
}
</script>

<script lang="ts">
const IDEAS = [
	{ icon: "lucide-database", text: "A DocType for " },
	{ icon: "lucide-blocks", text: "An app to " },
	{ icon: "lucide-globe", text: "A website for " },
	{ icon: "lucide-chart-column", text: "A dashboard of " },
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
}
</script>
