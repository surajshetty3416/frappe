<template>
	<ul class="divide-y divide-outline-gray-1">
		<li v-for="item in items" :key="`${item.kind}/${item.name}`">
			<div
				class="flex h-10 items-center gap-2.5 px-3 transition-colors duration-75"
				:class="[item.doctype ? 'cursor-pointer hover:bg-surface-gray-1' : '', open === item.name ? 'bg-surface-gray-1' : '']"
				@click="item.doctype && item.record && (open = open === item.name ? null : item.name)"
			>
				<span class="size-1.5 shrink-0 rounded-full" :class="DOT[item.kind]" :title="LABEL[item.kind]" />
				<span v-if="labelled" class="w-20 shrink-0 text-xs text-ink-gray-5">{{ LABEL[item.kind] }}</span>
				<span class="min-w-0 shrink truncate text-sm text-ink-gray-8">{{ item.title || item.text }}</span>
				<span class="min-w-0 flex-1 truncate text-sm text-ink-gray-5">{{ about(item) }}</span>
				<span class="shrink-0 text-xs tabular-nums text-ink-gray-4">{{ dayjs(item.modified).fromNow() }}</span>
				<!-- a decision or a piece of work opens to show what it is about; a mention is read in place -->
				<Button
					v-if="item.kind === 'mention'"
					size="sm"
					variant="subtle"
					:label="item.actions[0].label"
					:loading="busy === item.name"
					@click.stop="respond(item, 0, { values: {}, comment: '', reply: '' })"
				/>
				<Button
					v-else-if="item.doctype && item.record"
					size="sm"
					variant="subtle"
					:label="item.kind === 'approval' ? 'Review' : 'Open'"
					icon-right="lucide-chevron-down"
					@click.stop="open = open === item.name ? null : item.name"
				/>
			</div>
			<TaskCard
				v-if="open === item.name && item.doctype && item.record"
				:doctype="item.doctype"
				:name="item.record"
				:actions="item.actions"
				:perform="(i, input) => respond(item, i, input)"
			/>
		</li>
	</ul>
	<DoneList v-if="done.length" :entries="done" :fresh="fresh" :undoing="undoing" @undo="reopen" />
</template>

<script setup lang="ts">
import { Button, call, dayjs, toast } from "frappe-ui"
import { ref } from "vue"

import { refreshed } from "./home"
import DoneList, { type DoneEntry } from "./widgets/DoneList.vue"
import TaskCard, { type TaskAction, type TaskInput } from "./widgets/TaskCard.vue"
import { errorText } from "./widgets/format"

export interface InboxItem {
	kind: "assignment" | "approval" | "mention"
	name: string
	text: string
	doctype: string | null
	record: string | null
	title: string | null
	who: string | null
	facts: string[]
	due?: string | null
	modified: string
	actions: TaskAction[]
}

defineProps<{ items: InboxItem[]; done: DoneEntry[]; labelled?: boolean }>()

const LABEL: Record<InboxItem["kind"], string> = { approval: "Approval", assignment: "Assigned", mention: "Mention" }
const DOT: Record<InboxItem["kind"], string> = {
	approval: "bg-surface-amber-5",
	assignment: "bg-surface-blue-6",
	mention: "bg-surface-violet-6",
}

// who it is from and what is at stake, then what the person was told
const about = (item: InboxItem) =>
	[item.who, ...item.facts, item.title ? item.text : null, item.due ? `due ${dayjs(item.due).format("D MMM")}` : null]
		.filter(Boolean)
		.join(" · ")

const open = ref<string | null>(null)
const busy = ref<string | null>(null)
const fresh = ref<string | null>(null)
async function respond(item: InboxItem, action: number, input: TaskInput) {
	busy.value = item.name
	try {
		await call("frappe.ai.workspace.respond", {
			kind: item.kind,
			name: item.name,
			action: item.actions[action].label,
			comment: input.comment,
		})
		open.value = null
		fresh.value = item.name
		toast.success(`${item.actions[action].label}: ${item.title || item.text}`)
		refreshed.value++
	} catch (error) {
		toast.error(errorText(error))
	} finally {
		busy.value = null
	}
}

const undoing = ref<string | null>(null)
async function reopen(entry: DoneEntry) {
	undoing.value = entry.name
	try {
		await call("frappe.ai.workspace.reopen", { name: entry.name })
		fresh.value = null
		refreshed.value++
	} catch (error) {
		toast.error(errorText(error))
	} finally {
		undoing.value = null
	}
}
</script>
