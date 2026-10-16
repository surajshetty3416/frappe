<template>
	<!-- what the person finished here today, the latest first, each with what it did -->
	<div class="border-t border-outline-gray-1">
		<button
			type="button"
			class="flex h-8 w-full items-center gap-2 px-3 text-xs text-ink-gray-5 hover:text-ink-gray-7"
			@click="open = !open"
		>
			<span class="lucide-circle-check size-3.5 text-ink-green-5" />Done today
			<span class="tabular-nums">{{ entries.length }}</span>
			<span class="lucide-chevron-down ml-auto size-3.5 transition-transform" :class="open ? 'rotate-180' : ''" />
		</button>
		<ul v-if="open" class="divide-y divide-outline-gray-1 border-t border-outline-gray-1">
			<li
				v-for="entry in entries"
				:key="entry.name"
				class="flex h-9 items-center gap-3 px-3 transition-colors duration-300"
				:class="entry.name === fresh ? 'bg-surface-gray-2' : ''"
			>
				<span class="lucide-check size-3.5 shrink-0 text-ink-green-5" />
				<span class="min-w-0 shrink truncate text-sm text-ink-gray-7">{{ entry.title }}</span>
				<span class="min-w-0 flex-1 truncate text-sm text-ink-gray-5">{{ entry.what }}</span>
				<span class="shrink-0 text-xs tabular-nums text-ink-gray-4">{{ dayjs(entry.when).fromNow() }}</span>
				<Button v-if="entry.undo" size="sm" variant="ghost" label="Undo" :loading="undoing === entry.name" @click="$emit('undo', entry)" />
			</li>
		</ul>
	</div>
</template>

<script setup lang="ts">
import { Button, dayjs } from "frappe-ui"
import { ref, watch } from "vue"

export interface DoneEntry {
	name: string
	title: string
	what: string
	when: string
	undo: boolean
	kind?: "assignment" | "approval"
}

const props = defineProps<{ entries: DoneEntry[]; fresh?: string | null; undoing?: string | null }>()
defineEmits<{ undo: [entry: DoneEntry] }>()

// it opens on what was just finished, so the row that left the list is seen to land here
const open = ref(false)
watch(
	() => props.fresh,
	(fresh) => fresh && (open.value = true),
	{ immediate: true }
)
</script>
