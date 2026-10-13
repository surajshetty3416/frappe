<template>
	<template v-for="(part, i) in parts" :key="i">
		<span v-if="part.field" class="rounded-4 bg-surface-gray-3 px-0.5 py-0.5 text-ink-gray-8">{{ part.field }}</span>
		<code v-else-if="part.code" class="rounded-4 bg-surface-gray-3 px-1 py-0.5 font-mono text-xs text-ink-gray-8">{{ part.code }}</code>
		<template v-else>{{ part.text }}</template>
	</template>
</template>

<script setup lang="ts">
import type { PromptPart } from "../api"

defineProps<{ parts: PromptPart[] }>()
</script>
