<template>
	<SidebarRail>
		<nav class="flex w-full flex-1 flex-col items-center gap-2">
			<SidebarRailItem
				v-for="layer in layers"
				:key="layer.name"
				:label="layer.title"
				:icon="layer.icon"
				:route="layer.path"
				:active="activeLayer === layer.name"
				variant="ghost"
			/>
		</nav>
		<div class="flex flex-col items-center gap-2">
			<SidebarRailItem
				v-if="activeLayer !== 'flow'"
				label="Ask Flow"
				icon="lucide-sparkles"
				:active="assistantOpen"
				variant="ghost"
				@click="assistantOpen = !assistantOpen"
			/>
			<SidebarRailItem label="Desk" icon="lucide-layout-grid" href="/desk" variant="ghost" />
			<SidebarRailItem
				:label="isDark ? 'Light theme' : 'Dark theme'"
				:icon="isDark ? 'lucide-sun' : 'lucide-moon'"
				variant="ghost"
				@click="toggleColorScheme"
			/>
			<Dropdown :options="userMenu" side="right" align="end">
				<template #trigger>
					<SidebarRailItem :label="user" variant="ghost">
						<Avatar :label="user" size="md" />
					</SidebarRailItem>
				</template>
			</Dropdown>
		</div>
	</SidebarRail>
</template>

<script setup lang="ts">
import { Avatar, Dropdown, SidebarRail, SidebarRailItem, call, useColorScheme } from "frappe-ui"
import { computed } from "vue"
import { useRoute } from "vue-router"

import { assistantOpen } from "../assistant"
import { layers } from "../layers"
import { sessionUser } from "../session"

const route = useRoute()
const activeLayer = computed(() => route.matched[0]?.meta.layer)
const user = sessionUser()

const { resolvedColorScheme, toggleColorScheme } = useColorScheme()
const isDark = computed(() => resolvedColorScheme.value === "dark")

const userMenu = [
	{ label: "My settings", icon: "lucide-user", onClick: () => window.open(`/desk/user/${user}`) },
	{
		label: "Log out",
		icon: "lucide-log-out",
		onClick: () => call("logout").then(() => (window.location.href = "/login")),
	},
]
</script>
