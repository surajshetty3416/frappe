<template>
	<aside class="flex h-full flex-col bg-surface-base">
		<header data-layer="shell" class="flex h-12 shrink-0 items-center gap-1 border-b border-outline-gray-1 px-2">
			<Button
				v-for="tab in TABS"
				:key="tab.value"
				:variant="pane.tab === tab.value ? 'subtle' : 'ghost'"
				:label="tab.label"
				@click="pane.tab = tab.value"
			/>
			<span class="flex-1" />
			<!-- the open chat's menu, which the chat renders here -->
			<div v-show="pane.tab === 'chat'" id="studio-chat-menu" class="flex items-center" />
			<Button
				v-if="pane.tab === 'chat' && homeChat"
				variant="ghost"
				icon="lucide-square-pen"
				tooltip="New chat"
				@click="newChat"
			/>
			<Button
				v-if="pane.tab === 'chat' && homeChat"
				variant="ghost"
				icon="lucide-maximize-2"
				tooltip="Open in Studio"
				:route="`/studio/chat/${homeChat}`"
			/>
			<Button variant="ghost" icon="lucide-x" tooltip="Close" @click="pane.open = false" />
		</header>
		<!-- the chat mounts when first shown, as it cannot lay out hidden, and stays so its conversation goes on -->
		<div v-if="chatSeen" v-show="pane.tab === 'chat'" class="min-h-0 flex-1">
			<HomeChat />
		</div>
		<div v-if="pane.tab === 'details'" data-layer="shell" class="min-h-0 flex-1 overflow-y-auto">
			<ViewDetails v-if="openView" :view="openView" />
			<p v-else class="p-4 text-base text-ink-gray-5">Open a view to see its details.</p>
		</div>
	</aside>
</template>

<script setup lang="ts">
import { Button } from "frappe-ui"
import { ref, watchEffect } from "vue"

import HomeChat from "./HomeChat.vue"
import ViewDetails from "./ViewDetails.vue"
import { homeChat, openView, pane, question } from "./home"

const TABS = [
	{ label: "Chat", value: "chat" },
	{ label: "Details", value: "details" },
] as const

const chatSeen = ref(false)
watchEffect(() => pane.value.tab === "chat" && (chatSeen.value = true))

function newChat() {
	homeChat.value = null
	question.value = ""
}
</script>
