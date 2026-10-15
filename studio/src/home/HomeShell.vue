<template>
	<div class="relative flex h-full w-full overflow-hidden bg-surface-base">
		<HomeSidebar />
		<div class="relative flex min-w-0 flex-1 flex-col">
			<RouterView />
			<AskBar v-show="!chatOpen" />
		</div>
		<!-- beside the page on a wide screen, over its edge on a narrow one -->
		<RightPane
			v-if="paneSeen"
			v-show="pane.open"
			class="w-[400px] shrink-0 border-l border-outline-gray-1 max-xl:absolute max-xl:inset-y-0 max-xl:right-0 max-xl:z-20 max-xl:shadow-xl"
		/>
	</div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watchEffect } from "vue"

import AskBar from "./AskBar.vue"
import HomeSidebar from "./HomeSidebar.vue"
import RightPane from "./RightPane.vue"
import { askFocus, homeChat, loadHome, pane } from "./home"

// the chat in the pane has its own composer
const chatOpen = computed(() => pane.value.open && pane.value.tab === "chat")

loadHome()

// the pane mounts when first opened and stays, so its chat keeps its conversation while closed
const paneSeen = ref(false)
watchEffect(() => pane.value.open && (paneSeen.value = true))
// the conversation is the home's; Studio opens it as a chat of its own
onBeforeUnmount(() => (homeChat.value = null))

function onKeydown(event: KeyboardEvent) {
	if (!(event.metaKey || event.ctrlKey) || !["k", "j"].includes(event.key)) return
	event.preventDefault()
	if (chatOpen.value) pane.value.open = false
	askFocus.value++
}
onMounted(() => window.addEventListener("keydown", onKeydown))
onBeforeUnmount(() => window.removeEventListener("keydown", onKeydown))
</script>
