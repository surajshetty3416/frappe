<template>
	<aside data-layer="flow" class="flex h-full w-[420px] shrink-0 flex-col border-l border-outline-gray-1 bg-surface-base">
		<div class="flex h-10 shrink-0 items-center justify-between border-b border-outline-gray-1 pl-3 pr-1.5">
			<span class="text-sm font-medium text-ink-gray-8">Ask Flow</span>
			<div class="flex items-center gap-1">
				<Button variant="ghost" icon="lucide-maximize-2" route="/flow" tooltip="Open the chat" />
				<Button variant="ghost" icon="lucide-x" tooltip="Close" @click="assistantOpen = false" />
			</div>
		</div>
		<div class="relative min-h-0 flex-1">
			<FlowApp embedded />
		</div>
	</aside>
</template>

<script setup lang="ts">
import { Button } from "frappe-ui"
import { defineAsyncComponent } from "vue"

import { assistantOpen } from "../assistant"

const FlowApp = defineAsyncComponent(async () => {
	await import("@flow/index.css")
	return import("@flow/App.vue")
})
</script>
