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
			<div class="flex-1" />
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
import { Avatar, Dropdown, Sidebar, SidebarHeader, SidebarItem, call, useColorScheme } from "frappe-ui"
import { computed } from "vue"
import { useRoute } from "vue-router"

import { sessionUser } from "../session"
import { askFocus, home } from "./home"

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
