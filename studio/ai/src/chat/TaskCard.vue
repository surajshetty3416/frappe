<template>
	<button
		type="button"
		class="flex w-full items-start gap-3 rounded-6 border border-outline-gray-2 bg-surface-base px-3 py-2.5 text-left transition-colors hover:bg-surface-gray-1"
		:data-task-chat="task.chat"
		:data-task-status="status"
		@click="router.push({ name: 'studio-chat', params: { session: task.chat } })"
	>
		<span class="grid size-5 flex-none place-items-center">
			<LoadingIndicator v-if="status === 'Running'" class="size-4 text-ink-gray-5" />
			<span v-else :class="look.icon" class="size-4" />
		</span>
		<span class="min-w-0 flex-1">
			<span class="flex items-center gap-2">
				<span class="min-w-0 flex-1 truncate text-sm font-medium text-ink-gray-8">{{ title }}</span>
				<span class="flex-none text-sm" :class="look.text">{{ look.label }}</span>
			</span>
			<span class="mt-0.5 line-clamp-2 text-sm text-ink-gray-5">{{ task.message }}</span>
		</span>
		<span class="lucide-chevron-right mt-0.5 size-4 flex-none text-ink-gray-4" />
	</button>
</template>

<script setup>
import { computed, inject, onBeforeUnmount, ref } from "vue";
import { useRouter } from "vue-router";
import { useDebounceFn } from "@vueuse/core";
import { LoadingIndicator, call } from "frappe-ui";
import { chats } from "@shell/chats";
import { onListUpdate } from "@shell/realtime";

// One task the orchestrator sent to a chat, with that chat's turn's live status.
const props = defineProps({ task: { type: Object, required: true } });
const flow = inject("flow");
const router = useRouter();

const LOOKS = {
	Queued: { label: "Queued", icon: "lucide-clock text-ink-gray-5", text: "text-ink-gray-5" },
	Running: { label: "Running", icon: "", text: "text-ink-gray-5" },
	Paused: { label: "Waiting for approval", icon: "lucide-circle-pause text-ink-amber-6", text: "text-ink-amber-6" },
	Completed: { label: "Done", icon: "lucide-circle-check text-ink-green-6", text: "text-ink-gray-5" },
	Denied: { label: "Failed", icon: "lucide-circle-x text-ink-red-6", text: "text-ink-red-6" },
	Failed: { label: "Failed", icon: "lucide-circle-x text-ink-red-6", text: "text-ink-red-6" },
};
const ENDED = ["Completed", "Denied", "Failed"];

const status = ref(props.task.status ?? "Running");
const run = ref(props.task.run ?? null);
const look = computed(() => LOOKS[status.value] ?? LOOKS.Running);
const title = computed(() => chats.value.find((chat) => chat.name === props.task.chat)?.title || props.task.title);

async function load() {
	const session = flow.state.sessionId;
	if (!session || (run.value && ENDED.includes(status.value))) return;
	const found = await call("frappe.ai.orchestrator.get_task", {
		session,
		chat: props.task.chat,
		message: props.task.message,
		run: run.value,
	}).catch(() => null);
	if (!found) return;
	run.value = found.run;
	status.value = found.status;
}
load();
const stop = onListUpdate("Flow Run", useDebounceFn(load, 500));
onBeforeUnmount(stop);
</script>
