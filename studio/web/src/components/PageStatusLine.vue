<template>
	<div class="flex items-center gap-1.5 text-sm text-ink-gray-5">
		<PageStatusDot :page="page" />
		<span class="truncate">{{ time }}</span>
	</div>
</template>
<script setup lang="ts">
import PageStatusDot from "@web/components/PageStatusDot.vue";
import { BuilderPage } from "@web/types/doctypes";

defineProps<{
	page: BuilderPage;
	time: string;
}>();
</script>
