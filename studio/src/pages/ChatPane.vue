<template>
	<div class="hidden" />
</template>

<script setup lang="ts">
import { watch } from "vue"
import { useRoute, useRouter } from "vue-router"

import { getSessionArtifacts } from "../artifacts"

const route = useRoute()
const router = useRouter()

// the chat sits in the center column; this route only reopens the chat's latest artifact beside it
watch(
	() => route.params.session,
	async (param) => {
		const session = String(param)
		document.title = "Chat · Studio"
		if (!param || session === "new") return
		const latest = (await getSessionArtifacts(session)).at(-1)
		if (latest && route.params.session === session) router.replace({ path: latest.route, query: { chat: session } })
	},
	{ immediate: true }
)
</script>
