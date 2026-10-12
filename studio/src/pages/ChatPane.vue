<template>
	<div class="flex h-full items-center justify-center bg-surface-gray-1 p-8 text-center">
		<div class="max-w-sm">
			<span class="lucide-sparkles mx-auto block size-6 text-ink-gray-4" />
			<p class="mt-3 text-base font-medium text-ink-gray-8">What you build opens here</p>
			<p class="mt-1 text-p-sm text-ink-gray-6">
				Ask for a website, a dashboard or an app, and its editor opens beside the chat as soon as it exists.
			</p>
		</div>
	</div>
</template>

<script setup lang="ts">
import { onMounted } from "vue"
import { useRoute, useRouter } from "vue-router"

import { getSessionArtifacts } from "../artifacts"

const route = useRoute()
const router = useRouter()

// a chat that already made something reopens beside its latest artifact
onMounted(async () => {
	const session = String(route.params.session)
	document.title = "Chat · Studio"
	if (session === "new") return
	const artifacts = await getSessionArtifacts(session)
	const latest = artifacts.at(-1)
	if (latest && route.params.session === session) router.replace({ path: latest.route, query: { chat: session } })
})
</script>
