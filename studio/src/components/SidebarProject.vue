<template>
	<SidebarItem
		:label="project.title"
		:icon="open ? 'lucide-folder-open' : 'lucide-folder'"
		:route="projectRoute(project.name)"
		:active="route.name === 'studio-project' && project.name === activeProject"
	>
		<template #suffix>
			<button
				type="button"
				class="mr-1 grid size-5 place-items-center rounded-4 text-ink-gray-5 hover:bg-surface-gray-3 hover:text-ink-gray-7"
				:aria-label="open ? `Hide ${project.title}'s chats` : `Show ${project.title}'s chats`"
				:aria-expanded="open"
				@click="emit('toggle')"
			>
				<span class="lucide-chevron-right size-3.5 transition-transform duration-150" :class="open ? 'rotate-90' : ''" />
			</button>
		</template>
	</SidebarItem>
	<!-- an empty icon lane, so chat titles line up with the project's -->
	<template v-if="open">
		<SidebarItem
			v-for="chat in shown"
			:key="chat.name"
			:route="{ name: 'studio-chat', params: { session: chat.name } }"
			:active="chat.name === currentChat"
			:label="chat.title || 'Untitled chat'"
		>
			<template #prefix><span class="size-4" /></template>
			<template #suffix>
				<span class="mr-2 hidden pl-2 text-xs text-ink-gray-4 group-hover/sidebar-item:inline">{{ ago(chat.modified) }}</span>
			</template>
		</SidebarItem>
		<SidebarItem v-if="showAll || shown.length < chats.length" @click="showAll = !showAll">
			<template #prefix><span class="size-4" /></template>
			<span class="text-sm text-ink-gray-5">{{ showAll ? "Show less" : `Show ${chats.length - shown.length} more` }}</span>
		</SidebarItem>
	</template>
</template>

<script setup lang="ts">
import { SidebarItem, dayjs } from "frappe-ui"
import { computed, ref } from "vue"
import { useRoute } from "vue-router"

import type { Chat } from "../artifacts"
import { type Project, activeProject, projectRoute } from "../projects"

const CHATS_SHOWN = 5

// one project in the sidebar: its row, and its latest chats under it while open
const props = defineProps<{ project: Project; chats: Chat[]; open: boolean; currentChat: string | null }>()
const emit = defineEmits<{ toggle: [] }>()
const route = useRoute()

const showAll = ref(false)
// the open chat shows even when it is older than the first few
const shown = computed(() =>
	props.chats.filter((chat, index) => showAll.value || index < CHATS_SHOWN || chat.name === props.currentChat)
)

const ago = (modified: string) => {
	const minutes = dayjs().diff(dayjs(modified), "minute")
	if (minutes < 1) return "now"
	if (minutes < 60) return `${minutes}m`
	if (minutes < 60 * 24) return `${Math.floor(minutes / 60)}h`
	return `${Math.floor(minutes / 60 / 24)}d`
}
</script>
