<template>
	<FrappeUIProvider>
		<div class="flex h-full w-full overflow-hidden bg-surface-base">
			<StudioSidebar v-if="showShell" />
			<div class="flex min-w-0 flex-1 flex-col">
				<TopBar
					v-if="showShell"
					:title="title"
					:can-toggle-panel="canTogglePanel"
					:panel-visible="panelVisible"
					@toggle-panel="togglePanel"
				/>
				<div v-if="chatLayout" ref="body" class="flex min-h-0 flex-1">
					<div class="flex h-full min-w-0 flex-1 justify-center">
						<div class="h-full w-full" :class="panelVisible ? '' : 'max-w-[760px]'">
							<StudioChat />
						</div>
					</div>
					<div
						class="relative h-full shrink-0 overflow-hidden"
						:class="[resizing ? '' : 'transition-[width] duration-150 ease-out', panelVisible ? 'border-l border-outline-gray-1' : '']"
						:style="{ width: panelVisible ? `${layout.panelWidth}%` : '0px' }"
					>
						<div
							v-if="panelVisible"
							class="absolute inset-y-0 left-0 z-30 w-1.5 cursor-col-resize hover:bg-surface-gray-3"
							:class="resizing ? 'bg-surface-gray-3' : ''"
							@pointerdown="startResize"
						/>
						<EditorPanel>
							<RouterView />
						</EditorPanel>
					</div>
				</div>
				<div v-else class="relative min-h-0 flex-1">
					<RouterView />
				</div>
			</div>
		</div>
		<SearchDialog v-if="showShell" />
	</FrappeUIProvider>
</template>

<script setup lang="ts">
import { FrappeUIProvider } from "frappe-ui"
import { computed, onBeforeUnmount, onMounted, ref } from "vue"
import { useRoute, useRouter } from "vue-router"

import { chats } from "./chats"
import EditorPanel from "./components/EditorPanel.vue"
import SearchDialog from "./components/SearchDialog.vue"
import StudioChat from "./components/StudioChat.vue"
import StudioSidebar from "./components/StudioSidebar.vue"
import TopBar from "./components/TopBar.vue"
import { layers } from "./layers"
import { layout, searchOpen } from "./layout"
import { isLoggedIn } from "./session"
import { tabs } from "./tabs"

const route = useRoute()
const router = useRouter()

const showShell = computed(() => isLoggedIn() && !route.matched.some((record) => record.meta.hideRail))
const onArtifact = computed(() => route.matched.some((record) => record.meta.artifact))
// a chat, or an artifact's editor with the chat that builds it
const chatLayout = computed(
	() => showShell.value && (route.name === "studio-home" || route.name === "studio-chat" || onArtifact.value)
)
const panelVisible = computed(() => chatLayout.value && onArtifact.value && layout.value.panelOpen)
const canTogglePanel = computed(() => chatLayout.value && (onArtifact.value || tabs.value.length > 0))

const currentChat = computed(() => {
	const session = route.name === "studio-chat" ? route.params.session : route.query.chat
	return typeof session === "string" && session !== "new" ? session : null
})
const title = computed(() => {
	// the chat's title; the artifact's is on the artifact bar
	if (chatLayout.value) {
		if (!currentChat.value) return "New chat"
		return chats.value.find((chat) => chat.name === currentChat.value)?.title || "Untitled chat"
	}
	return layers.find((layer) => layer.name === route.matched[0]?.meta.layer)?.title ?? "Studio"
})

function togglePanel() {
	if (onArtifact.value) {
		layout.value.panelOpen = !layout.value.panelOpen
		return
	}
	// from a chat, the panel opens on the last tab
	const last = tabs.value.at(-1)
	if (!last) return
	layout.value.panelOpen = true
	router.push(last.path)
}

const body = ref<HTMLElement | null>(null)
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
	else if (event.key === "n" && !event.shiftKey) router.push("/studio")
	else return
	event.preventDefault()
}
onMounted(() => window.addEventListener("keydown", onKeydown))
onBeforeUnmount(() => window.removeEventListener("keydown", onKeydown))
</script>
