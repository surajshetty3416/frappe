<template>
	<DropdownButton v-if="flow.state.sessionId" :options="menu" align="end" variant="ghost" icon="lucide-ellipsis" tooltip="Chat" aria-label="Chat" />
</template>

<script setup>
import { computed, inject } from "vue"
import DropdownButton from "./DropdownButton.vue"
import { dialog } from "frappe-ui/src/utils/dialog"

import { conversationTitle, formatTokens } from "../transcript.js"

const flow = inject("flow")

const title = computed(() => flow.state.session?.title ?? conversationTitle(flow.state.conversation) ?? "")

// how much of the model's context the chat fills; opens the step-by-step transcript
const usage = computed(() => {
	const { contextTokens, contextWindow, usage } = flow.state.conversation
	if (contextTokens && contextWindow) return `${formatTokens(contextTokens)} of ${formatTokens(contextWindow)} tokens`
	if (contextTokens) return `${formatTokens(contextTokens)} tokens`
	const spent = usage.input + usage.output
	return spent ? `${formatTokens(spent)} tokens` : "Transcript"
})

const menu = computed(() => [
	{ label: "Rename", icon: "lucide-pen", onClick: promptRename },
	{ label: usage.value, icon: "lucide-list", onClick: () => flow.setTranscriptOpen(true) },
	{ label: "Delete", icon: "lucide-trash-2", theme: "red", onClick: confirmDelete },
])

function promptRename() {
	dialog.prompt({
		title: "Rename chat",
		fields: [{ name: "title", label: "Title", default: title.value }],
		confirmLabel: "Rename",
		onConfirm: (values) => {
			if (values.title?.trim()) void flow.renameSession(values.title.trim())
		},
	})
}

function confirmDelete() {
	dialog.confirm({
		title: "Delete chat?",
		message: "The chat and its messages are deleted. What it made stays.",
		actions: [
			{ label: "Cancel", variant: "outline" },
			{ label: "Delete", variant: "solid", theme: "red", onClick: () => void flow.deleteSession() },
		],
	})
}
</script>
