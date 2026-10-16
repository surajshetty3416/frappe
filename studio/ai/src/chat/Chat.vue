<template>
	<!-- a new chat scrolls as one page, so a long list under the composer pushes nothing out of view -->
	<div class="relative flex h-full min-h-0 flex-col bg-surface-base text-base text-ink-gray-8" :class="blank ? 'overflow-y-auto' : ''">
		<!-- the shell's top bar carries the open chat's menu -->
		<Teleport to="#studio-chat-menu" defer>
			<!-- this layer's styles stop at the shell's top bar, so the menu carries its own mark -->
			<div data-layer="ai" class="contents">
				<ChatMenu :key="viewKey" />
			</div>
		</Teleport>
		<!-- a new chat: the host's intro over the composer, its starters under it -->
		<!-- centered over the composer, or at the top when the starters under it are a page of their own -->
		<div v-if="blank" class="flex flex-col justify-end px-4 pb-6 pt-12" :class="introAtTop ? 'flex-none' : 'flex-[1_0_auto]'">
			<slot name="intro" />
		</div>
		<ReplayIntro v-else-if="replayIntro" :key="`replay-intro-${viewKey}`" :replay="replayIntro" />
		<MessageList v-else :key="`messages-${viewKey}`">
			<template #end>
				<div
					v-if="replayError"
					data-replay-error
					class="whitespace-pre-wrap break-words rounded-4 border border-outline-red-1 bg-surface-red-1 px-3 py-2 text-sm text-ink-red-6"
				>{{ replayError }}</div>
			</template>
		</MessageList>
		<ReplayBar v-if="!readOnly" :key="`replay-bar-${viewKey}`" />
		<Composer v-if="!readOnly" ref="composer" :key="`composer-${viewKey}`" />
		<p v-else class="flex-none px-4 pb-4 text-center text-sm text-ink-gray-5">
			Only the owner of this chat can send messages.
		</p>
		<div v-if="blank" class="flex-[1_0_auto] px-4 pb-6">
			<slot name="starters" :prefill="(text) => composer?.prefill(text)" />
		</div>
		<TranscriptDialog :key="`transcript-${viewKey}`" />
	</div>
</template>

<script setup>
import { computed, onBeforeUnmount, provide, reactive, ref, shallowRef, watch } from "vue";
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
import { isReplaying, pauseReplay, replays } from "@shell/replay";
import ReplayBar from "./ReplayBar.vue";
import ReplayIntro from "./ReplayIntro.vue";
import TaskCard from "./TaskCard.vue";
import { presentTool } from "./toolMeta.js";

const props = defineProps({
	boot: { type: Object, required: true },
	// what the editor beside the chat tells the agent with each message (the store's `context` option)
	context: { type: Object, default: null },
	// the chat on screen (none is a new one) and a first message to send
	session: { type: String, default: null },
	// the Studio project a new chat starts in
	project: { type: String, default: null },
	initialMessage: { type: String, default: "" },
	introAtTop: { type: Boolean, default: false },
	// a host that only converses, such as the home, offers no orchestration and says what to type
	orchestrate: { type: Boolean, default: true },
	placeholder: { type: String, default: null },
	// (artifact) => icon class, for the artifact cards in the transcript
	artifactIcon: { type: Function, default: null },
});
// "session" when the chat on screen gets its session or loses it (null when it is deleted),
// "artifact" when its tool hands one back live or a card is clicked
const emit = defineEmits(["session", "artifact"]);

// Every chat opened here keeps its own store, so a chat switched away from keeps streaming
// and its queue keeps sending; the components on screen read the shown chat's store.
const MAX_CHATS = 8;
const socket = connectSocket(props.boot);
// someone else's chat is view-only: its tools would run as its owner
const readOnlyBySession = reactive({});
const client = new FrappeClient({
	socket,
	boot: props.boot,
	transport,
	hooks: {
		onSession: (payload) => (readOnlyBySession[payload.name] = Boolean(payload.read_only)),
		project: () => props.project,
	},
});
const stores = [];
// a new chat builds, or sends each task to the chat that owns its artifacts or to a new one
const AGENTS = [
	{ agent: null, label: "Build" },
	{ agent: "Orchestrator", label: "Orchestrate", placeholder: "Describe the work; each task goes to its own chat…", skills: false },
];
const shown = shallowRef(null);
const viewKey = ref(0);

function createStore() {
	const store = createFlowStore(client, {
		storageKey: `studio.chat.${props.boot.user?.name ?? "user"}`,
		presentTool,
		openArtifact: (artifact) => store === shown.value && emit("artifact", artifact),
		artifactIcon: (artifact) => props.artifactIcon?.(artifact),
		// a replay keeps its turn open from step to step, and folds it once it finished
		openTurn: () => {
			const replay = replays.get(store.state.sessionId);
			return Boolean(replay && !replay.live && replay.status !== "Done");
		},
		// Stop and Escape pause a replay, so the step at work keeps its tool calls
		stop: (session) => {
			const replay = replays.get(session);
			if (!replay || replay.live || !(isReplaying(session) || replay.status === "Playing")) return false;
			pauseReplay(session);
			return true;
		},
		context: props.context,
		agents: props.orchestrate ? AGENTS : AGENTS.slice(0, 1),
		...(props.placeholder ? { placeholder: props.placeholder } : {}),
		taskCard: TaskCard,
	});
	watch(
		() => store.state.toast,
		(item) => {
			if (!item) return;
			if (item.kind === "error") toast.error(item.message);
			else toast.success(item.message);
		}
	);
	stores.push(store);
	return store;
}

const isBlank = (store) => !store.state.sessionId && !store.state.conversation.sending.length;
const busy = (store) =>
	store.state.conversation.running || store.state.conversation.sending.length || store.state.queued.length;

// the chats beyond the limit that are idle and off screen close, the longest unseen first
function prune() {
	for (const store of [...stores]) {
		if (stores.length <= MAX_CHATS) return;
		if (store === shown.value || busy(store)) continue;
		store.detach();
		stores.splice(stores.indexOf(store), 1);
	}
}

function show(session) {
	let store = stores.find((open) => (session ? open.state.sessionId === session : isBlank(open)));
	const opening = !store;
	store ??= createStore();
	if (store !== shown.value) {
		stores.splice(stores.indexOf(store), 1);
		stores.push(store);
		shown.value = store;
		viewKey.value++;
	}
	if (opening && session) void store.openSession(session);
	prune();
	return store;
}

const flow = new Proxy({}, { get: (_, key) => shown.value?.[key] });
provide("flow", flow);
show(props.session);
watch(
	() => props.session,
	(session) => session !== shown.value.state.sessionId && show(session)
);
// a blank chat moved to another project offers that project's skills
watch(
	() => props.project,
	() => isBlank(shown.value) && shown.value.startNewChat()
);
watch(
	() => [props.session, props.initialMessage],
	([session, message]) => !session && message && isBlank(shown.value) && void shown.value.send(message),
	{ immediate: true }
);

const readOnly = computed(() => Boolean(readOnlyBySession[shown.value?.state.sessionId]));
const composer = ref(null);
// a chat never sent to starts like a new one
const unsent = (store) =>
	!store.state.loading && !store.state.conversation.entries.length && !store.state.conversation.running && !busy(store);
// a replay not yet played is not a new chat: its recording waits
const blank = computed(
	() => !props.initialMessage && (props.session ? unsent(shown.value) && !replays.get(props.session) : isBlank(shown.value))
);

// a replay not yet played shows what it will replay, over its Play
const replayIntro = computed(() => {
	const id = shown.value.state.sessionId;
	const replay = id && replays.get(id);
	const waiting = replay && !replay.step && replay.status === "Ready" && !replay.live;
	return waiting && unsent(shown.value) && !isReplaying(id) ? replay : null;
});

// why a replay stopped, under the step that failed
const replayError = computed(() => {
	const replay = replays.get(shown.value.state.sessionId);
	return (replay && !replay.live && replay.error) || "";
});

// the shown chat got its session, or lost it
watch(
	() => [shown.value, shown.value.state.sessionId],
	([store, id], [before]) => store === before && emit("session", id)
);

// an artifact the shown chat's tool makes or changes live opens beside the chat
let seen = 0;
watch(
	() => [shown.value, shown.value.state.conversation.entries.length],
	([store, length], [before]) => {
		if (store === before) {
			const live = store.state.session?.latest_seq ?? 0;
			for (const entry of store.state.conversation.entries.slice(seen, length)) {
				const artifact = entry.type === "tool_result" && entry.seq > live && resultArtifact(entry);
				if (artifact) emit("artifact", artifact);
			}
		}
		seen = length;
	}
);

// an editor beside the chat sends a message as if the person typed it
defineExpose({
	send(message) {
		if (readOnly.value) return false;
		shown.value.send(message);
		return true;
	},
});

onBeforeUnmount(() => {
	for (const store of stores) store.detach();
	socket.disconnect();
});
</script>
