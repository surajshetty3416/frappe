<template>
	<header data-layer="shell" class="flex h-12 shrink-0 items-center gap-2 border-b border-outline-gray-1 px-2">
		<Button
			variant="ghost"
			icon="lucide-panel-left"
			:tooltip="layout.sidebarOpen ? 'Hide sidebar (⌘\\)' : 'Show sidebar (⌘\\)'"
			@click="layout.sidebarOpen = !layout.sidebarOpen"
		/>
		<nav class="flex min-w-0 flex-1 items-center gap-1.5 text-base">
			<template v-if="crumb">
				<RouterLink :to="crumb.route" class="max-w-[40%] shrink-0 truncate text-ink-gray-5 hover:text-ink-gray-8">{{ crumb.label }}</RouterLink>
				<span class="shrink-0 text-ink-gray-4">/</span>
			</template>
			<h1 class="min-w-0 truncate font-medium text-ink-gray-8">{{ title }}</h1>
		</nav>
		<!-- the open chat's menu, which the chat renders here -->
		<div id="studio-chat-menu" class="flex items-center" />
		<Button
			v-if="canTogglePanel"
			variant="ghost"
			icon="lucide-panel-right"
			:tooltip="panelVisible ? 'Hide editor' : 'Show editor'"
			@click="emit('toggle-panel')"
		/>
	</header>
</template>

<script setup lang="ts">
import { Button } from "frappe-ui"
import type { RouteLocationRaw } from "vue-router"

import { layout } from "../layout"

defineProps<{
	title: string
	crumb: { label: string; route: RouteLocationRaw } | null
	canTogglePanel: boolean
	panelVisible: boolean
}>()
const emit = defineEmits<{ "toggle-panel": [] }>()
</script>
