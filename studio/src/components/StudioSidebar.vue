<template>
	<div
		data-layer="shell"
		class="h-full shrink-0 overflow-hidden border-outline-gray-1 transition-[width] duration-150 ease-out"
		:class="layout.sidebarOpen ? 'w-[260px] border-r' : 'w-0'"
	>
		<Sidebar :collapsible="false" width="260px" aria-label="Studio">
			<SidebarHeader title="Studio" :logo="STUDIO_LOGO" />
			<div class="flex flex-col gap-0.5 px-2">
				<SidebarItem label="New chat" icon="lucide-square-pen" :route="newChatRoute(activeProject)" :active="route.name === 'studio-home'">
					<template #suffix><span class="mr-2 text-xs text-ink-gray-4">⌘N</span></template>
				</SidebarItem>
				<SidebarItem label="Search" icon="lucide-search" @click="searchOpen = true">
					<template #suffix><span class="mr-2 text-xs text-ink-gray-4">⌘K</span></template>
				</SidebarItem>
			</div>
			<div class="mt-4 flex flex-col gap-0.5 px-2">
				<SidebarItem
					v-for="kind in artifactKinds"
					:key="kind.kind"
					:label="kind.title"
					:icon="kind.icon"
					:route="{ name: 'studio-artifacts', params: { kind: kind.kind } }"
					:active="route.name === 'studio-artifacts' && route.params.kind === kind.kind"
				/>
			</div>

			<div class="mt-4 flex min-h-0 flex-1 flex-col overflow-y-auto px-2 pb-2">
				<div class="flex items-center justify-between">
					<SidebarLabel>Projects</SidebarLabel>
					<Button variant="ghost" size="sm" icon="lucide-plus" tooltip="New project" @click="creating = true" />
				</div>
				<div v-if="!projectsLoaded" class="flex h-7 items-center pl-2">
					<LoadingIndicator class="size-3.5 text-ink-gray-4" />
				</div>
				<p v-else-if="!projects.length" class="px-2 py-1 text-sm text-ink-gray-5">Everything you build starts in a project.</p>
				<div v-else class="flex flex-col gap-0.5">
					<SidebarProject
						v-for="project in projects"
						:key="project.name"
						:project="project"
						:chats="chatsOf(project.name)"
						:open="openProjects.includes(project.name)"
						:current-chat="currentChat"
						@toggle="toggle(project.name)"
					/>
				</div>
			</div>

			<div class="flex flex-col gap-0.5 border-t border-outline-gray-1 p-2">
				<SidebarItem label="Settings" icon="lucide-settings" route="/studio/settings" :active="route.matched[0]?.meta.layer === 'settings'" />
				<Dropdown :options="userMenu" side="top" align="start">
					<template #trigger>
						<SidebarItem :label="fullName">
							<template #prefix><Avatar :label="fullName" size="sm" /></template>
						</SidebarItem>
					</template>
				</Dropdown>
			</div>
		</Sidebar>
		<ProjectDialog v-model:open="creating" />
	</div>
</template>

<script setup lang="ts">
import { useStorage } from "@vueuse/core"
import {
	Avatar,
	Button,
	Dropdown,
	LoadingIndicator,
	Sidebar,
	SidebarHeader,
	SidebarItem,
	SidebarLabel,
	call,
	useColorScheme,
} from "frappe-ui"
import { computed, ref, watch } from "vue"
import { useRoute } from "vue-router"

import { artifactKinds } from "../artifacts"
import { chats, superseded, watchChats } from "../chats"
import { layout, searchOpen } from "../layout"
import { activeProject, newChatRoute, projects, projectsLoaded, watchProjects } from "../projects"
import { sessionUser } from "../session"
import ProjectDialog from "./ProjectDialog.vue"
import SidebarProject from "./SidebarProject.vue"

const STUDIO_LOGO = `${import.meta.env.BASE_URL}studio-logo.svg`

const route = useRoute()
const currentChat = computed(() => {
	const session = route.name === "studio-chat" ? route.params.session : route.query.chat
	return typeof session === "string" && session !== "new" ? session : null
})
const creating = ref(false)

watchProjects()
watchChats()
const listed = computed(() => chats.value.filter((chat) => chat.name === currentChat.value || !superseded.value.has(chat.name)))
const chatsOf = (project: string) => listed.value.filter((chat) => chat.project === project)

// the projects whose chats show, kept across reloads; the one on screen opens
const openProjects = useStorage<string[]>("studio-open-projects", [])
watch(activeProject, (project) => project && !openProjects.value.includes(project) && openProjects.value.push(project), {
	immediate: true,
})
function toggle(project: string) {
	const open = openProjects.value
	if (open.includes(project)) open.splice(open.indexOf(project), 1)
	else open.push(project)
}

const user = sessionUser()
const fullName = decodeURIComponent(document.cookie.match(/full_name=([^;]*)/)?.[1] ?? user).replace(/\+/g, " ")

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
