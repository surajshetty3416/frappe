<template>
	<section v-if="recordings.length" data-recordings>
		<h2 class="px-2 text-sm font-medium text-ink-gray-5">Recorded chats</h2>
		<!-- a plain row, so recordings line up with the Recent rows below them -->
		<button
			v-for="recording in recordings"
			:key="recording.name"
			type="button"
			class="mt-1 flex h-9 w-full items-center gap-2 rounded-4 px-2 text-left hover:bg-surface-gray-2 disabled:cursor-default"
			:disabled="Boolean(starting)"
			@click="start(recording.name)"
		>
			<LoadingIndicator v-if="starting === recording.name" class="size-4 shrink-0 text-ink-gray-5" />
			<span v-else class="lucide-play size-4 shrink-0 text-ink-gray-5" />
			<span class="min-w-0 flex-1 truncate text-base text-ink-gray-8">{{ recording.title }}</span>
			<span class="shrink-0 text-sm text-ink-gray-5">{{ recording.steps }} steps</span>
			<span class="w-28 shrink-0 whitespace-nowrap text-right text-sm text-ink-gray-4">{{ dayjs(recording.creation).fromNow() }}</span>
		</button>
	</section>
</template>

<script setup lang="ts">
import { LoadingIndicator, dayjs } from "frappe-ui"
import { onMounted, ref } from "vue"
import { useRouter } from "vue-router"

import { type Recording, listRecordings, startReplay } from "../replay"

// recorded chats replay into a new chat, in the order the demo walks them
const router = useRouter()
const recordings = ref<Recording[]>([])
const starting = ref<string | null>(null)

onMounted(async () => (recordings.value = await listRecordings().catch(() => [])))

async function start(recording: string) {
	starting.value = recording
	try {
		const replay = await startReplay(recording)
		router.push({ name: "studio-chat", params: { session: replay.session } })
	} finally {
		starting.value = null
	}
}
</script>
