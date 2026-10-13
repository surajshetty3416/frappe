<template>
	<div v-if="shown" class="flex-none px-4 pb-2" data-replay-bar>
		<div class="mx-auto flex h-9 max-w-[760px] items-center gap-1 rounded-6 border border-outline-gray-1 bg-surface-gray-1 px-1 text-sm">
			<template v-if="replay.status === 'Done'">
				<span class="lucide-circle-check ml-1.5 size-4 flex-none text-ink-gray-5" />
				<span class="ml-1 flex-1 text-ink-gray-8">Replay finished</span>
				<Button
					v-if="next"
					class="min-w-0 max-w-[60%]"
					size="sm"
					variant="solid"
					icon-right="lucide-arrow-right"
					:loading="starting"
					:label="`Next: ${next.title}`"
					@click="start(next.name)"
				/>
			</template>
			<!-- the transcript shows what failed, in full -->
			<template v-else-if="replay.status === 'Failed'">
				<span class="lucide-circle-alert ml-1.5 size-4 flex-none text-ink-red-5" />
				<span class="ml-1 flex-1 tabular-nums text-ink-gray-8">Stopped at step {{ replay.step }} of {{ replay.steps }}</span>
				<Button
					size="sm"
					icon-left="lucide-rotate-ccw"
					label="Retry"
					tooltip="Replay the recording again in a new chat"
					:loading="starting"
					@click="start(replay.recording)"
				/>
			</template>
			<template v-else>
				<Button
					v-if="playing"
					variant="ghost"
					icon="lucide-pause"
					tooltip="Pause after this step"
					aria-label="Pause"
					@click="pauseReplay(session)"
				/>
				<Button
					v-else
					variant="ghost"
					icon="lucide-play"
					tooltip="Play to the end"
					aria-label="Play"
					:disabled="!ready"
					@click="playReplay(session, flow.state)"
				/>
				<Button
					variant="ghost"
					icon="lucide-step-forward"
					tooltip="Play one step"
					aria-label="Step"
					:disabled="!ready || playing"
					@click="stepReplay(session, flow.state)"
				/>
				<span class="ml-1 flex-none tabular-nums text-ink-gray-8">{{ progress }}</span>
				<span class="flex-1" />
				<DropdownButton :options="speedOptions" align="end" variant="ghost" :label="`${speed}x`" icon-right="lucide-chevron-down" tooltip="Replay speed" />
			</template>
		</div>
	</div>
</template>

<script setup>
import { computed, inject, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { Button } from "frappe-ui";
import DropdownButton from "@flow/ui-core/components/DropdownButton.vue";

import {
	isPlaying,
	isStepping,
	loadReplay,
	nextRecording,
	pauseReplay,
	playReplay,
	replays,
	speed,
	speeds,
	startReplay,
	stepReplay,
} from "@shell/replay";

// The controls of a replayed chat, until its person sends a message of their own.
const flow = inject("flow");
const router = useRouter();

const session = computed(() => flow.state.sessionId);
const replay = computed(() => (session.value && replays.get(session.value)) || null);
const playing = computed(() => isPlaying(session.value));
const stepping = computed(() => isStepping(session.value));
const inFlight = computed(() => stepping.value || replay.value?.status === "Playing");
const ready = computed(() => replay.value?.status === "Ready" && !inFlight.value);
const spoke = computed(() => flow.state.queued.length > 0 || flow.state.conversation.sending.length > 0);
const shown = computed(() => replay.value && !replay.value.live && !(spoke.value && !stepping.value));

const speedOptions = computed(() =>
	speeds.map((value) => ({
		label: `${value}x`,
		icon: speed.value === value ? "lucide-check" : undefined,
		onClick: () => (speed.value = value),
	}))
);

const progress = computed(() => {
	const { step, steps } = replay.value;
	if (inFlight.value) return `Step ${step + 1} of ${steps}`;
	return step ? `Step ${step} of ${steps}` : `${steps} steps`;
});

watch(session, (id) => id && void loadReplay(id), { immediate: true });
// a run this bar did not start is a live message, or a step another tab played
watch(
	() => flow.state.conversation.running,
	() => session.value && replays.get(session.value) && !stepping.value && void loadReplay(session.value)
);

const next = ref(null);
watch(
	() => replay.value?.status === "Done" && replay.value.recording,
	async (recording) => (next.value = recording ? await nextRecording(recording) : null),
	{ immediate: true }
);

const starting = ref(false);
async function start(recording) {
	starting.value = true;
	try {
		const started = await startReplay(recording);
		router.push({ name: "studio-chat", params: { session: started.session } });
	} finally {
		starting.value = false;
	}
}
</script>
