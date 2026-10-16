<template>
	<div data-layer="shell" class="h-full w-[232px] shrink-0 overflow-hidden border-r border-outline-gray-1">
		<Sidebar :collapsible="false" width="232px" aria-label="Main navigation">
			<SidebarHeader :title="organization" :logo="LOGO" />
			<div class="flex flex-col gap-0.5 px-2">
				<SidebarItem label="Home" icon="lucide-house" route="/home" :active="route.name === 'home'" />
				<SidebarItem label="Inbox" icon="lucide-inbox" route="/home/inbox" :active="route.name === 'home-inbox'">
					<template #suffix>
						<span v-if="inboxCount" class="mr-2 text-xs tabular-nums text-ink-gray-5">{{ inboxCount }}</span>
					</template>
				</SidebarItem>
				<SidebarItem label="Search or ask" icon="lucide-search" @click="askFocus++">
					<template #suffix><kbd class="mr-2 font-mono text-xs text-ink-gray-4">⌘K</kbd></template>
				</SidebarItem>
			</div>

			<div class="mt-4 flex min-h-0 flex-1 flex-col overflow-y-auto px-2 pb-2">
				<div class="flex items-center justify-between pr-1">
					<SidebarLabel>Spaces</SidebarLabel>
					<Button variant="ghost" size="sm" icon="lucide-plus" tooltip="Find or join a Space" @click="finding = true" />
				</div>
				<div class="flex flex-col gap-0.5">
					<SidebarItem
						v-for="space in spaces?.mine"
						:key="space.name"
						:label="space.title"
						:icon="spaceIcon(space.icon)"
						:route="`/home/s/${encodeURIComponent(space.name)}`"
						:active="route.name === 'home-space' && route.params.space === space.name"
					/>
					<button
						v-if="spaces && !spaces.mine.length"
						type="button"
						class="rounded-4 px-2 py-1.5 text-left text-sm text-ink-gray-5 hover:bg-surface-gray-2"
						@click="finding = true"
					>
						Join your team's Space to see its work here.
					</button>
				</div>
			</div>

			<div class="flex flex-col gap-0.5 border-t border-outline-gray-1 p-2">
				<SidebarItem v-if="home?.can_build" label="Studio" icon="lucide-pencil-ruler" route="/studio" />
				<Dropdown :options="userMenu" side="top" align="start">
					<template #trigger>
						<SidebarItem :label="fullName">
							<template #prefix><Avatar :label="fullName" size="sm" /></template>
						</SidebarItem>
					</template>
				</Dropdown>
			</div>
		</Sidebar>
		<SpacesDialog v-model:open="finding" />
		<PersonaDialog v-model:open="switching" />
	</div>
</template>

<script setup lang="ts">
import { Avatar, Button, Dropdown, Sidebar, SidebarHeader, SidebarItem, SidebarLabel, call, useColorScheme } from "frappe-ui"
import { computed, ref } from "vue"
import { useRoute } from "vue-router"

import { sessionUser } from "../session"
import PersonaDialog from "./PersonaDialog.vue"
import SpacesDialog from "./SpacesDialog.vue"
import { askFocus, home, inboxCount, loadInboxCount, loadSpaces, personas, spaceIcon, spaces, workspace } from "./home"

const LOGO = `${import.meta.env.BASE_URL}studio-logo.svg`

const route = useRoute()
const finding = ref(false)
const switching = ref(false)

loadSpaces()
loadInboxCount()

const organization = computed(() => workspace.value?.organization || "Home")
const fullName = decodeURIComponent(document.cookie.match(/full_name=([^;]*)/)?.[1] ?? sessionUser()).replace(/\+/g, " ")

const { resolvedColorScheme, toggleColorScheme } = useColorScheme()
const userMenu = computed(() => [
	...(personas.value.length ? [{ label: "Switch persona", icon: "lucide-repeat", onClick: () => (switching.value = true) }] : []),
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
