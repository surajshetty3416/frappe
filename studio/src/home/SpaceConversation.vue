<template>
	<!-- the conversation an app provides for the Space, or what people did on its records -->
	<iframe v-if="space.conversation?.url" :key="space.conversation.url" :src="space.conversation.url" :title="`${space.title} conversation`" class="size-full border-0" />
	<div v-else class="flex h-full flex-col overflow-y-auto">
		<p class="border-b border-outline-gray-1 px-3 py-2 text-xs text-ink-gray-5">
			Recent activity on this Space's records. Install a chat app such as Raven to talk here.
		</p>
		<div v-if="!activity" class="flex flex-col gap-2 p-3">
			<Skeleton v-for="i in 4" :key="i" class="h-4 w-full rounded" />
		</div>
		<p v-else-if="!activity.length" class="px-3 py-3 text-sm text-ink-gray-5">Nothing yet.</p>
		<ul v-else class="flex flex-col">
			<li
				v-for="entry in activity"
				:key="entry.name"
				class="flex cursor-pointer gap-2.5 px-3 py-2 hover:bg-surface-gray-1"
				@click="showRecord(entry.reference_doctype, entry.reference_name)"
			>
				<Avatar :label="entry.owner" size="sm" class="mt-0.5" />
				<div class="min-w-0 flex-1">
					<p class="truncate text-xs text-ink-gray-5">
						{{ entry.owner }} · {{ entry.reference_doctype }} {{ entry.reference_name }} · {{ dayjs(entry.creation).fromNow() }}
					</p>
					<p class="line-clamp-2 text-sm text-ink-gray-8">{{ plain(entry.content) }}</p>
				</div>
			</li>
		</ul>
	</div>
</template>

<script setup lang="ts">
import { Avatar, Skeleton, call, dayjs } from "frappe-ui"
import { ref, watch } from "vue"

import { type Space, showRecord } from "./home"

const props = defineProps<{ space: Space }>()

interface Entry {
	name: string
	reference_doctype: string
	reference_name: string
	content: string
	owner: string
	creation: string
}

const activity = ref<Entry[] | null>(null)
watch(
	() => props.space.name,
	async (space) => {
		if (props.space.conversation?.url) return
		activity.value = null
		activity.value = await call<Entry[]>("frappe.ai.spaces.get_activity", { space }).catch(() => [])
	},
	{ immediate: true }
)

const plain = (html: string) => new DOMParser().parseFromString(html || "", "text/html").body.textContent?.trim() ?? ""
</script>
