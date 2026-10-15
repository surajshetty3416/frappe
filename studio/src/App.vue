<template>
	<!-- frappe-ui's provider, with a light toast at the top that leaves on its own -->
	<Toaster
		position="top-center"
		:close-button="false"
		:duration="3000"
		:visible-toasts="3"
		:icons="TOAST_ICONS"
		:toast-options="{
			unstyled: true,
			classes: {
				toast: 'flex items-center gap-2 rounded-6 border border-outline-gray-2 bg-surface-base px-3 py-2 shadow-lg w-fit max-w-[420px]',
				title: 'text-sm text-ink-gray-8',
				description: 'text-sm text-ink-gray-5',
				icon: 'flex size-4 shrink-0 items-center',
				actionButton: 'ml-2 h-6 shrink-0 rounded-4 px-2 text-sm font-medium text-ink-gray-8 hover:bg-surface-gray-2',
			},
		}"
	/>
	<div class="flex h-full w-full overflow-hidden bg-surface-base">
		<StudioSidebar v-if="showShell" />
		<div class="flex min-w-0 flex-1 flex-col">
			<TopBar
				v-if="showShell"
				:title="title"
				:crumb="crumb"
			/>
			<div v-if="chatLayout" ref="body" class="flex min-h-0 flex-1">
				<!-- beside the editor the chat keeps room for its composer's controls; the editor gives way -->
				<div class="flex h-full flex-1 justify-center" :class="panelVisible ? 'min-w-[440px]' : 'min-w-0'">
					<div class="h-full w-full" :class="panelVisible ? '' : 'max-w-[760px]'">
						<StudioChat />
					</div>
				</div>
				<div
					class="relative h-full overflow-hidden"
					:class="[resizing ? '' : 'transition-[width] duration-150 ease-out', panelVisible ? 'border-l border-outline-gray-1' : '']"
					:style="{ width: panelVisible ? `${layout.panelWidth}%` : '0px' }"
				>
					<div
						v-if="panelVisible"
						class="absolute inset-y-0 left-0 z-30 w-1.5 cursor-col-resize hover:bg-surface-gray-3"
						:class="resizing ? 'bg-surface-gray-3' : ''"
						@pointerdown="startResize"
					/>
					<!-- the panel lays out at its final width and slides in whole from the window's edge, so nothing squashes or
					     clips at its left on the way -->
					<div class="absolute inset-y-0 left-0" :style="{ width: `${panelPixels}px` }">
						<EditorPanel>
							<RouterView />
						</EditorPanel>
					</div>
				</div>
			</div>
			<div v-else class="relative min-h-0 flex-1">
				<RouterView />
			</div>
		</div>
	</div>
	<SearchDialog v-if="showShell" />
	<Dialogs />
</template>

<script setup lang="ts">
import { useElementSize } from "@vueuse/core"
import { Dialogs } from "frappe-ui"
import { computed, h, onBeforeUnmount, onMounted, ref, watch, watchEffect } from "vue"
import { useRoute, useRouter } from "vue-router"

import { artifactKind } from "./artifacts"
import { chats, loadChats } from "./chats"
import EditorPanel from "./components/EditorPanel.vue"
import SearchDialog from "./components/SearchDialog.vue"
import StudioChat from "./components/StudioChat.vue"
import StudioSidebar from "./components/StudioSidebar.vue"
import TopBar from "./components/TopBar.vue"
import { layers } from "./layers"
import { layout, searchOpen } from "./layout"
import { activeProject, lastProject, newChatRoute, projectRoute, projectTitle, routeProject } from "./projects"
import { isLoggedIn } from "./session"
import { tabChat } from "./tabs"
import { Toaster } from "vue-sonner"
import "vue-sonner/style.css"

const icon = (name: string) => h("span", { class: `${name} size-4` })
const TOAST_ICONS = {
	success: icon("lucide-circle-check text-ink-green-6"),
	error: icon("lucide-circle-alert text-ink-red-6"),
	warning: icon("lucide-triangle-alert text-ink-amber-6"),
	info: icon("lucide-info text-ink-gray-5"),
}

const route = useRoute()
const router = useRouter()

const showShell = computed(() => isLoggedIn() && !route.matched.some((record) => record.meta.hideRail))
const onArtifact = computed(() => route.matched.some((record) => record.meta.artifact))
// the home's or a project's new chat, a chat, or an artifact's editor with the chat that builds it
const CHAT_ROUTES = ["studio-home", "studio-project", "studio-chat"]
const chatLayout = computed(() => showShell.value && (CHAT_ROUTES.includes(String(route.name)) || onArtifact.value))
// an artifact's editor always shows beside its chat
const panelVisible = computed(() => chatLayout.value && onArtifact.value)

const currentChat = computed(() => {
	const session = route.name === "studio-chat" ? route.params.session : route.query.chat
	return typeof session === "string" && session !== "new" ? session : null
})
watchEffect(() => (tabChat.value = currentChat.value))
watchEffect(() => {
	const project = routeProject(route)
	activeProject.value = project
	if (project) lastProject.value = project
})
const openChat = computed(() => chats.value.find((chat) => chat.name === currentChat.value))
// a chat started here, like a replay, is not in the list until the list hears of it
watch(currentChat, (session) => session && !openChat.value && loadChats())
const title = computed(() => {
	if (route.name === "studio-project") return projectTitle(activeProject.value)
	if (route.name === "studio-artifacts") return artifactKind(route)?.title ?? ""
	// the chat's title; the artifact's is on the artifact bar
	if (chatLayout.value) {
		if (!currentChat.value) return "New chat"
		if (!openChat.value) return ""
		return openChat.value.title || "Untitled chat"
	}
	return layers.find((layer) => layer.name === route.matched[0]?.meta.layer)?.title ?? "Studio"
})

// a chat sits under its project
const crumb = computed(() =>
	chatLayout.value && activeProject.value && route.name !== "studio-project"
		? { label: projectTitle(activeProject.value), route: projectRoute(activeProject.value) }
		: null
)

const body = ref<HTMLElement | null>(null)
const { width: bodyWidth } = useElementSize(body)
// the chat keeps 440px beside the panel; the panel's border takes 1px
const panelPixels = computed(() => Math.min((bodyWidth.value * layout.value.panelWidth) / 100, bodyWidth.value - 440) - 1)
const resizing = ref(false)
function startResize(event: PointerEvent) {
	const area = body.value?.getBoundingClientRect()
	if (!area) return
	event.preventDefault()
	resizing.value = true
	const move = (moved: PointerEvent) => {
		const share = ((area.right - moved.clientX) / area.width) * 100
		layout.value.panelWidth = Math.round(Math.min(75, Math.max(35, share)) * 10) / 10
	}
	const stop = () => {
		resizing.value = false
		window.removeEventListener("pointermove", move)
		window.removeEventListener("pointerup", stop)
	}
	window.addEventListener("pointermove", move)
	window.addEventListener("pointerup", stop)
}

function onKeydown(event: KeyboardEvent) {
	if (!showShell.value || !(event.metaKey || event.ctrlKey)) return
	if (event.key === "k") searchOpen.value = true
	else if (event.key === "\\") layout.value.sidebarOpen = !layout.value.sidebarOpen
	else if (event.key === "n" && !event.shiftKey) router.push(newChatRoute(activeProject.value))
	else return
	event.preventDefault()
}
onMounted(() => window.addEventListener("keydown", onKeydown))
onBeforeUnmount(() => window.removeEventListener("keydown", onKeydown))
</script>
