<template>
	<header data-layer="shell" class="flex h-12 shrink-0 items-center gap-2 border-b border-outline-gray-1 px-2">
		<Button
			variant="ghost"
			icon="lucide-panel-left"
			:tooltip="layout.sidebarOpen ? 'Hide sidebar (⌘\\)' : 'Show sidebar (⌘\\)'"
			@click="layout.sidebarOpen = !layout.sidebarOpen"
		/>
		<h1 class="min-w-0 flex-1 truncate text-base font-medium text-ink-gray-8">{{ title }}</h1>
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

import { layout } from "../layout"

defineProps<{ title: string; canTogglePanel: boolean; panelVisible: boolean }>()
const emit = defineEmits<{ "toggle-panel": [] }>()
</script>
