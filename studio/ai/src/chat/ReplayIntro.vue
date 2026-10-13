<template>
	<div class="flex min-h-0 flex-1 items-center overflow-y-auto px-4" data-replay-intro>
		<div class="mx-auto w-full max-w-[760px]">
			<p class="text-sm text-ink-gray-5">Recorded chat</p>
			<h1 class="mt-1 text-2xl font-semibold text-ink-gray-9">{{ replay.title }}</h1>
			<!-- the clamp sits inside the padding, so no cut line shows under the ellipsis -->
			<div v-if="message" class="mt-4 rounded-6 bg-surface-gray-1 px-4 py-3">
				<p class="line-clamp-4 whitespace-pre-wrap text-base text-ink-gray-5">{{ message }}</p>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue";

import { cleanUserText } from "../api/events.js";

// A replay not yet played: what it will show, before its first step. The bar under it plays it.
const props = defineProps({ replay: { type: Object, required: true } });

const message = computed(() => cleanUserText(props.replay.message).text.trim());
</script>
