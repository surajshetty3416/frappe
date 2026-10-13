<template>
	<div class="flex min-h-0 flex-1 items-center overflow-y-auto px-4" data-replay-intro>
		<div class="mx-auto w-full max-w-[760px]">
			<p class="text-sm text-ink-gray-5">Recorded chat</p>
			<h1 class="mt-1 text-2xl font-semibold text-ink-gray-9">{{ replay.title }}</h1>
			<p v-if="message" class="mt-4 line-clamp-4 whitespace-pre-wrap rounded-6 bg-surface-gray-1 px-4 py-3 text-base text-ink-gray-5">{{ message }}</p>
			<div class="mt-4 flex items-center gap-3">
				<Button variant="solid" size="md" icon-left="lucide-play" label="Play" @click="playReplay(replay.session, flow.state)" />
				<span class="text-sm text-ink-gray-5">Press Play to replay {{ replay.steps }} steps</span>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, inject } from "vue";
import { Button } from "frappe-ui";

import { playReplay } from "@shell/replay";
import { cleanUserText } from "../api/events.js";

// A replay not yet played: what it will show, before its first step.
const props = defineProps({ replay: { type: Object, required: true } });
const flow = inject("flow");

const message = computed(() => cleanUserText(props.replay.message).text.trim());
</script>
