<template>
	<FrappeUIProvider>
		<div class="flex h-full w-full overflow-hidden bg-surface-base">
			<AppRail v-if="showRail" />
			<StudioChat v-if="showChat" />
			<div class="relative h-full min-w-0 flex-1">
				<RouterView />
			</div>
		</div>
	</FrappeUIProvider>
</template>

<script setup lang="ts">
import { FrappeUIProvider } from "frappe-ui"
import { computed } from "vue"
import { useRoute } from "vue-router"

import AppRail from "./components/AppRail.vue"
import StudioChat from "./components/StudioChat.vue"
import { isLoggedIn } from "./session"

const route = useRoute()
const showRail = computed(() => isLoggedIn() && !route.matched.some((record) => record.meta.hideRail))
// a chat, or an artifact's editor: the chat sits on the left of whatever it builds
const showChat = computed(
	() => showRail.value && (route.name === "studio-chat" || route.matched.some((record) => record.meta.artifact))
)
</script>
