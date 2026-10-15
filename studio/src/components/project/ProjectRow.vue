<template>
	<component
		:is="to ? RouterLink : 'div'"
		v-bind="to ? { to } : {}"
		class="group flex min-h-11 items-center gap-3 rounded-4 px-2 py-1.5"
		:class="to ? 'hover:bg-surface-gray-2' : ''"
	>
		<span class="grid size-4 shrink-0 place-items-center text-ink-gray-5">
			<slot name="prefix"><span v-if="icon" :class="icon" class="size-4" /></slot>
		</span>
		<span class="flex min-w-0 flex-1 flex-col">
			<span class="truncate text-base text-ink-gray-8">{{ title }}</span>
			<span v-if="subtitle" class="truncate text-sm text-ink-gray-5">{{ subtitle }}</span>
		</span>
		<span class="flex shrink-0 items-center gap-2 text-sm text-ink-gray-5">
			<slot name="suffix" />
		</span>
	</component>
</template>

<script setup lang="ts">
import { RouterLink, type RouteLocationRaw } from "vue-router"

// One row of a project's list: a fixed icon lane, the title over its detail, and a trailing lane.
defineProps<{ title: string; subtitle?: string | null; icon?: string; to?: RouteLocationRaw | null }>()
</script>
