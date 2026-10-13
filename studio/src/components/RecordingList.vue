<template>
	<section v-if="recordings.length" data-recordings>
		<h2 class="px-2 text-sm font-medium text-ink-gray-5">Recorded chats</h2>
		<Button
			v-for="recording in recordings"
			:key="recording.name"
			variant="ghost"
			class="mt-1 w-full"
			icon-left="lucide-play"
			:loading="starting === recording.name"
			:disabled="Boolean(starting)"
			@click="start(recording.name)"
		>
			<span class="min-w-0 flex-1 truncate text-left text-ink-gray-8">{{ recording.title }}</span>
			<template #suffix>
				<span class="text-sm text-ink-gray-5">{{ recording.steps }} steps</span>
			</template>
		</Button>
	</section>
</template>

<script setup lang="ts">
import { Button } from "frappe-ui"
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
