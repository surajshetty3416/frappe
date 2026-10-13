<template>
	<div data-layer="ai" class="flex h-full w-full flex-col bg-surface-base">
		<FlowApp
			v-if="ready"
			:key="mountKey"
			embedded
			:session="mountSession"
			:initial-message="initialMessage"
			:opened="opened"
			@session="onSession"
			@artifact="onArtifact"
		/>
		<div v-else class="flex flex-1 items-center justify-center">
			<LoadingIndicator class="size-4 text-ink-gray-5" />
		</div>
	</div>
</template>

<script setup lang="ts">
import { LoadingIndicator } from "frappe-ui"
import { computed, defineAsyncComponent, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"

import { type Artifact, getArtifactSession, linkArtifact, routeArtifact } from "../artifacts"

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

// `current` is the chat on screen; the chat is only remounted when the route asks for another one
const current = ref<string | null>(null)
const mountSession = ref<string | null>(null)
const mountKey = ref(0)
const ready = ref(false)
const initialMessage = ref("")

async function resolve() {
	let wanted = routeSession.value
	if (!wanted && artifact.value && !onChatRoute.value) {
		wanted = (await getArtifactSession(artifact.value.doctype, artifact.value.name))?.name ?? null
	}
	if (ready.value && wanted === current.value) return
	initialMessage.value = onChatRoute.value && typeof route.query.prompt === "string" ? route.query.prompt : ""
	current.value = mountSession.value = wanted
	mountKey.value++
	ready.value = true
}
watch(() => [routeSession.value, artifact.value?.doctype, artifact.value?.name], resolve, { immediate: true })

function onSession(session: string) {
	if (session === current.value) return
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

// the editor beside the chat, so "this page" in a message has a referent
const opened = () => (artifact.value ? { title: document.title, path: route.fullPath } : null)
</script>
