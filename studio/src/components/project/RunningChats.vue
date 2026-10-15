<template>
	<section v-if="running.length" class="flex flex-col">
		<h2 class="flex h-9 items-center px-2 text-sm font-medium text-ink-gray-6">Running now</h2>
		<ProjectRow
			v-for="chat in running"
			:key="chat.name"
			:to="{ name: 'studio-chat', params: { session: chat.name } }"
			:title="chat.title || 'Untitled chat'"
			:subtitle="chat.tasks ? `${chat.tasks.done} of ${chat.tasks.total} tasks done` : null"
		>
			<template #prefix>
				<span v-if="chat.status === 'Paused'" class="lucide-circle-pause size-4 text-ink-amber-6" />
				<LoadingIndicator v-else class="size-3.5 text-ink-gray-5" />
			</template>
			<template #suffix>
				<span v-if="chat.tasks" class="h-1 w-20 overflow-hidden rounded-full bg-surface-gray-3">
					<span class="block h-full rounded-full bg-surface-gray-7" :style="{ width: `${(chat.tasks.done / chat.tasks.total) * 100}%` }" />
				</span>
				<Badge v-if="chat.status === 'Paused'" theme="amber" label="Waiting for approval" />
				<Badge v-else theme="blue" label="Running" />
			</template>
		</ProjectRow>
	</section>
</template>

<script setup lang="ts">
import { useDebounceFn } from "@vueuse/core"
import { Badge, LoadingIndicator } from "frappe-ui"
import { onBeforeUnmount, ref, watch } from "vue"

import { type RunningChat, getRunningChats } from "../../projects"
import { onListUpdate } from "../../realtime"
import ProjectRow from "./ProjectRow.vue"

// the project's chats at work now, each with its status and how far its routed tasks got
const props = defineProps<{ project: string }>()
const running = ref<RunningChat[]>([])

async function load() {
	const project = props.project
	const list = await getRunningChats(project).catch(() => [])
	if (project === props.project) running.value = list
}
watch(() => props.project, load, { immediate: true })

const reload = useDebounceFn(load, 400)
const stops = ["Flow Run", "Flow Session"].map((doctype) => onListUpdate(doctype, reload))
onBeforeUnmount(() => stops.forEach((stop) => stop()))
</script>
