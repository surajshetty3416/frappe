<template>
	<div data-layer="shell" class="h-full w-[240px] shrink-0 overflow-hidden border-r border-outline-gray-1">
		<Sidebar :collapsible="false" width="240px" aria-label="Home">
			<SidebarHeader title="Home" :logo="LOGO" />
			<div class="flex flex-col gap-0.5 px-2">
				<SidebarItem label="Home" icon="lucide-house" route="/home" :active="route.name === 'home'" />
				<SidebarItem label="Search or ask" icon="lucide-search" @click="askFocus++">
					<template #suffix><span class="mr-2 text-xs text-ink-gray-4">⌘K</span></template>
				</SidebarItem>
			</div>
			<div class="mt-4 flex flex-col gap-0.5 px-2">
				<SidebarLabel>Browse</SidebarLabel>
				<SidebarItem
					v-for="kind in artifactKinds"
					:key="kind.kind"
					:label="kind.title"
					:icon="kind.icon"
					:route="`/home/${kind.kind}`"
					:active="route.params.kind === kind.kind && route.name === 'home-kind'"
				/>
			</div>
			<div class="mt-4 flex min-h-0 flex-1 flex-col gap-0.5 overflow-y-auto px-2 pb-2">
				<SidebarLabel>Pinned</SidebarLabel>
				<p v-if="home && !home.pinned.length" class="px-2 py-1 text-sm text-ink-gray-5">Pin a view to keep it here.</p>
				<SidebarItem
					v-for="artifact in home?.pinned"
					:key="`${artifact.doctype}/${artifact.name}`"
					:label="artifact.title"
					:icon="artifactIcon(artifact)"
					:route="viewRoute(artifact)"
					:active="route.path === viewRoute(artifact)"
				/>
			</div>
			<div class="flex flex-col gap-0.5 border-t border-outline-gray-1 p-2">
				<SidebarItem v-if="home?.can_build" label="Open Studio" icon="lucide-pencil-ruler" route="/studio" />
				<Dropdown :options="userMenu" side="top" align="start">
					<template #trigger>
						<SidebarItem :label="fullName">
							<template #prefix><Avatar :label="fullName" size="sm" /></template>
						</SidebarItem>
					</template>
				</Dropdown>
			</div>
		</Sidebar>
	</div>
</template>

<script setup lang="ts">
import { Avatar, Dropdown, Sidebar, SidebarHeader, SidebarItem, SidebarLabel, call, useColorScheme } from "frappe-ui"
import { computed } from "vue"
import { useRoute } from "vue-router"

import { artifactIcon, artifactKinds } from "../artifacts"
import { sessionUser } from "../session"
import { askFocus, home, viewRoute } from "./home"

const LOGO = `${import.meta.env.BASE_URL}studio-logo.svg`

const route = useRoute()

const fullName = decodeURIComponent(document.cookie.match(/full_name=([^;]*)/)?.[1] ?? sessionUser()).replace(/\+/g, " ")

const { resolvedColorScheme, toggleColorScheme } = useColorScheme()
const userMenu = computed(() => [
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
