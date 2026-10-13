<template>
	<div
		data-layer="shell"
		class="h-full shrink-0 overflow-hidden border-outline-gray-1 transition-[width] duration-150 ease-out"
		:class="layout.sidebarOpen ? 'w-[260px] border-r' : 'w-0'"
	>
		<Sidebar :collapsible="false" width="260px" aria-label="Studio">
			<SidebarHeader title="Studio">
				<template #prefix>
					<span class="grid size-7 place-items-center bg-surface-gray-10 text-ink-base">
						<span class="lucide-sparkles size-4" />
					</span>
				</template>
			</SidebarHeader>
			<div class="flex flex-col gap-0.5 px-2">
				<SidebarItem label="New chat" icon="lucide-square-pen" route="/studio" :active="route.name === 'studio-home'">
					<template #suffix><span class="mr-2 text-xs text-ink-gray-4">⌘N</span></template>
				</SidebarItem>
				<SidebarItem label="Search" icon="lucide-search" @click="searchOpen = true">
					<template #suffix><span class="mr-2 text-xs text-ink-gray-4">⌘K</span></template>
				</SidebarItem>
			</div>

			<div class="mt-4 flex min-h-0 flex-1 flex-col overflow-y-auto px-2 pb-2">
				<SidebarLabel>Build</SidebarLabel>
				<div class="flex flex-col gap-0.5">
					<SidebarItem
						v-for="layer in buildLayers"
						:key="layer.name"
						:label="layer.title"
						:icon="layer.icon"
						:route="layer.path"
						:active="activeLayer === layer.name"
					/>
				</div>

				<SidebarLabel class="mt-4">Chats</SidebarLabel>
				<div v-if="!loaded" class="flex h-7 items-center pl-2">
					<LoadingIndicator class="size-3.5 text-ink-gray-4" />
				</div>
				<p v-else-if="!chats.length" class="px-2 py-1 text-sm text-ink-gray-5">Your chats show up here.</p>
				<div v-else class="flex flex-col gap-0.5">
					<SidebarItem
						v-for="chat in chats"
						:key="chat.name"
						:route="{ name: 'studio-chat', params: { session: chat.name } }"
						:active="chat.name === currentChat"
						:label="chat.title || 'Untitled chat'"
					>
						<!-- the status takes the icon column, so titles line up with the layers -->
						<template #prefix>
							<span class="grid size-4 place-items-center">
								<LoadingIndicator v-if="chatStatus(chat, currentChat) === 'running'" class="size-3.5 text-ink-gray-5" />
								<Tooltip v-else-if="chatStatus(chat, currentChat) === 'waiting'" text="Waiting for approval">
									<span class="size-2 rounded-full bg-surface-amber-3" />
								</Tooltip>
								<span v-else-if="chatStatus(chat, currentChat) === 'unread'" class="size-2 rounded-full bg-surface-blue-6" />
							</span>
						</template>
						<template #suffix>
							<span class="mr-2 hidden pl-2 text-xs text-ink-gray-4 group-hover/sidebar-item:inline">{{ ago(chat.modified) }}</span>
						</template>
					</SidebarItem>
				</div>
			</div>

			<div class="flex flex-col gap-0.5 border-t border-outline-gray-1 p-2">
				<SidebarItem label="Settings" icon="lucide-settings" route="/studio/settings" :active="activeLayer === 'settings'" />
				<Dropdown :options="userMenu" side="top" align="start">
					<template #trigger>
						<SidebarItem :label="fullName">
							<template #prefix><Avatar :label="fullName" size="xs" /></template>
						</SidebarItem>
					</template>
				</Dropdown>
			</div>
		</Sidebar>
	</div>
</template>

<script setup lang="ts">
import {
	Avatar,
	Dropdown,
	LoadingIndicator,
	Sidebar,
	SidebarHeader,
	SidebarItem,
	SidebarLabel,
	Tooltip,
	call,
	dayjs,
	useColorScheme,
} from "frappe-ui"
import { computed, watch } from "vue"
import { useRoute } from "vue-router"

import { chatStatus, chats, loaded, markSeen, watchChats } from "../chats"
import { layers } from "../layers"
import { layout, searchOpen } from "../layout"
import { sessionUser } from "../session"

const route = useRoute()
const activeLayer = computed(() => {
	const layer = route.matched[0]?.meta.layer
	// the chats and the home belong to no layer of their own
	return route.name === "studio-home" || route.name === "studio-chat" || route.query.chat ? null : layer
})
const currentChat = computed(() => {
	const session = route.name === "studio-chat" ? route.params.session : route.query.chat
	return typeof session === "string" ? session : null
})

watchChats()
watch(
	() => [currentChat.value, chats.value],
	() => currentChat.value && markSeen(currentChat.value),
	{ immediate: true }
)

const ago = (modified: string) => {
	const minutes = dayjs().diff(dayjs(modified), "minute")
	if (minutes < 1) return "now"
	if (minutes < 60) return `${minutes}m`
	if (minutes < 60 * 24) return `${Math.floor(minutes / 60)}h`
	return `${Math.floor(minutes / 60 / 24)}d`
}

const user = sessionUser()
const fullName = decodeURIComponent(document.cookie.match(/full_name=([^;]*)/)?.[1] ?? user).replace(/\+/g, " ")

// Settings sits at the bottom, not among the layers a person builds with
const buildLayers = layers.filter((layer) => layer.name !== "settings" && !layer.hidden)

const { resolvedColorScheme, toggleColorScheme } = useColorScheme()
const userMenu = computed(() => [
	{ label: "AI model", icon: "lucide-cpu", route: "/studio/settings/model" },
	{
		label: resolvedColorScheme.value === "dark" ? "Light theme" : "Dark theme",
		icon: resolvedColorScheme.value === "dark" ? "lucide-sun" : "lucide-moon",
		onClick: toggleColorScheme,
	},
	{
		label: "Log out",
		icon: "lucide-log-out",
		onClick: () => call("logout").then(() => (window.location.href = "/login")),
	},
])
</script>
