<template>
	<FrappeUIProvider>
		<div class="flex h-full w-full overflow-hidden bg-surface-base">
			<AppRail v-if="showRail" />
			<div class="relative h-full min-w-0 flex-1">
				<RouterView />
			</div>
			<AssistantPanel v-if="showAssistant" />
		</div>
	</FrappeUIProvider>
</template>

<script setup lang="ts">
import { FrappeUIProvider } from "frappe-ui"
import { computed } from "vue"
import { useRoute } from "vue-router"

import { assistantOpen } from "./assistant"
import AppRail from "./components/AppRail.vue"
import AssistantPanel from "./components/AssistantPanel.vue"
import { isLoggedIn } from "./session"

const route = useRoute()
const showRail = computed(() => isLoggedIn() && !route.matched.some((record) => record.meta.hideRail))
const showAssistant = computed(() => showRail.value && assistantOpen.value && route.matched[0]?.meta.layer !== "flow")
</script>
