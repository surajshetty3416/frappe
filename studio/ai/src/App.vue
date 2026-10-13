<template>
	<Chat v-if="boot" :boot="boot" v-bind="$attrs" />
	<div v-else class="flex h-full items-center justify-center bg-surface-base px-6 text-center">
		<p v-if="error" class="max-w-md text-base text-ink-gray-6">{{ error }}</p>
		<LoadingIndicator v-else class="size-4 text-ink-gray-5" />
	</div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { LoadingIndicator } from "frappe-ui";

import { loadBoot } from "./boot.js";
import Chat from "./chat/Chat.vue";

// session, initialMessage, opened and the session and artifact events reach the chat
defineOptions({ inheritAttrs: false });

const boot = ref(null);
const error = ref("");

onMounted(async () => {
	try {
		boot.value = await loadBoot();
	} catch (err) {
		error.value = err?.message ?? "The chat could not load.";
	}
});
</script>
