<template>
	<div class="relative flex h-full min-h-0 flex-col bg-surface-base text-base text-ink-gray-8">
		<ChatMenu class="absolute right-3 top-2 z-10" />
		<MessageList />
		<Composer v-if="!readOnly" />
		<p v-else class="flex-none px-4 pb-4 text-center text-sm text-ink-gray-5">
			Only the owner of this chat can send messages.
		</p>
		<TranscriptDialog />
	</div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, provide, ref, watch } from "vue";
import { toast } from "frappe-ui";
import ChatMenu from "@flow/ui-core/components/ChatMenu.vue";
import Composer from "@flow/ui-core/components/Composer.vue";
import MessageList from "@flow/ui-core/components/MessageList.vue";
import TranscriptDialog from "@flow/ui-core/components/TranscriptDialog.vue";
import { createFlowStore } from "@flow/ui-core/store.js";
import { resultArtifact } from "@flow/ui-core/transcript.js";

import { FrappeClient } from "../api/client.js";
import * as transport from "../api/frappe.js";
import { connectSocket } from "../api/socket.js";
import { presentTool } from "./toolMeta.js";

const props = defineProps({
	boot: { type: Object, required: true },
	// what the user has open beside the chat ({ title, path }), sent with each message
	opened: { type: Function, default: null },
	// the chat to open (none starts a new one) and a first message to send
	session: { type: String, default: null },
	initialMessage: { type: String, default: "" },
});
// "session" when the open chat changes, "artifact" when a tool hands one back live or a card is clicked
const emit = defineEmits(["session", "artifact"]);

// someone else's chat is view-only: its tools would run as its owner
const readOnly = ref(false);
const socket = connectSocket(props.boot);
const client = new FrappeClient({
	socket,
	boot: props.boot,
	transport,
	hooks: {
		onSession: (payload) => (readOnly.value = Boolean(payload.read_only)),
		opened: () => props.opened?.(),
	},
});
const store = createFlowStore(client, {
	storageKey: `studio.chat.${props.boot.user?.name ?? "user"}`,
	presentTool,
	openArtifact: (artifact) => emit("artifact", artifact),
});
provide("flow", store);

watch(
	() => store.state.toast,
	(item) => {
		if (!item) return;
		if (item.kind === "error") toast.error(item.message);
		else toast.success(item.message);
	}
);

watch(
	() => store.state.sessionId,
	(id) => {
		if (!id) readOnly.value = false;
		else emit("session", id);
	}
);

// an artifact a tool makes or changes live opens beside the chat
let seen = 0;
watch(
	() => store.state.conversation.entries.length,
	(length) => {
		const live = store.state.session?.latest_seq ?? 0;
		for (const entry of store.state.conversation.entries.slice(seen, length)) {
			const artifact = entry.type === "tool_result" && entry.seq > live && resultArtifact(entry);
			if (artifact) emit("artifact", artifact);
		}
		seen = length;
	}
);

onMounted(async () => {
	if (props.session) await store.openSession(props.session);
	if (props.initialMessage) await store.send(props.initialMessage);
});
onBeforeUnmount(() => {
	store.detach();
	socket.disconnect();
});
</script>
