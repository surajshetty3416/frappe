<template>
	<div data-layer="shell" class="h-full overflow-y-auto">
		<div class="mx-auto flex w-full max-w-[1100px] flex-col gap-3 px-5 pb-28 pt-4">
			<header class="flex h-9 items-center gap-3">
				<h1 class="text-lg font-semibold text-ink-gray-9">Inbox</h1>
				<div class="mr-auto flex items-center gap-1">
					<Button
						v-for="filter in FILTERS"
						:key="filter.value"
						size="sm"
						:variant="kind === filter.value ? 'subtle' : 'ghost'"
						:label="`${filter.label}${counts[filter.value] ? ` ${counts[filter.value]}` : ''}`"
						@click="kind = filter.value"
					/>
				</div>
			</header>
			<div class="overflow-hidden rounded-3 border border-outline-gray-2">
				<div v-if="!items" class="flex flex-col gap-2 p-3">
					<Skeleton v-for="i in 5" :key="i" class="h-4 w-full rounded" />
				</div>
				<p v-else-if="!shown.length" class="flex items-center gap-2 px-3 py-3 text-sm text-ink-gray-5">
					<span class="lucide-check size-3.5" />Nothing waits on you here.
				</p>
				<ul v-else class="divide-y divide-outline-gray-1">
					<li
						v-for="item in shown"
						:key="`${item.kind}/${item.name}`"
						class="group flex h-11 items-center gap-3 px-3 transition-colors duration-75"
						:class="item.doctype ? 'cursor-pointer hover:bg-surface-gray-1' : ''"
						@click="item.doctype && item.record && showRecord(item.doctype, item.record, item.title ?? undefined)"
					>
						<span class="size-1.5 shrink-0 rounded-full" :class="DOT[item.kind]" />
						<span class="w-24 shrink-0 text-xs text-ink-gray-5">{{ LABEL[item.kind] }}</span>
						<span class="min-w-0 shrink truncate text-sm text-ink-gray-8">{{ item.title || item.text }}</span>
						<span class="min-w-0 flex-1 truncate text-sm text-ink-gray-5">{{ item.title ? item.text : item.doctype }}</span>
						<span class="shrink-0 text-xs tabular-nums text-ink-gray-4">{{ dayjs(item.modified).fromNow() }}</span>
						<span class="flex shrink-0 items-center gap-1" @click.stop>
							<Button
								v-for="(action, i) in item.actions"
								:key="action"
								size="sm"
								:variant="i === 0 ? 'subtle' : 'ghost'"
								:label="action"
								:loading="busy === `${item.name}/${action}`"
								@click="respond(item, action)"
							/>
						</span>
					</li>
				</ul>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { Button, Skeleton, call, dayjs, toast } from "frappe-ui"
import { computed, ref, watch } from "vue"

import { inboxCount, openView, refreshed, showRecord } from "./home"
import { errorText } from "./widgets/format"

interface Item {
	kind: "assignment" | "approval" | "mention"
	name: string
	text: string
	doctype: string | null
	record: string | null
	title: string | null
	modified: string
	actions: string[]
}

const FILTERS = [
	{ label: "All", value: "all" },
	{ label: "Approvals", value: "approval" },
	{ label: "Assigned", value: "assignment" },
	{ label: "Mentions", value: "mention" },
] as const
const LABEL: Record<Item["kind"], string> = { approval: "Approval", assignment: "Assigned", mention: "Mention" }
const DOT: Record<Item["kind"], string> = {
	approval: "bg-surface-amber-5",
	assignment: "bg-surface-blue-6",
	mention: "bg-surface-violet-6",
}

openView.value = null
document.title = "Inbox"

const items = ref<Item[] | null>(null)
async function load() {
	items.value = await call<Item[]>("frappe.ai.workspace.get_inbox").catch(() => [])
	inboxCount.value = items.value.length
}
watch(refreshed, load, { immediate: true })

const kind = ref<(typeof FILTERS)[number]["value"]>("all")
const shown = computed(() => (items.value ?? []).filter((item) => kind.value === "all" || item.kind === kind.value))
const counts = computed(() => {
	const all: Record<string, number> = { all: items.value?.length ?? 0 }
	for (const item of items.value ?? []) all[item.kind] = (all[item.kind] ?? 0) + 1
	return all
})

const busy = ref<string | null>(null)
async function respond(item: Item, action: string) {
	busy.value = `${item.name}/${action}`
	try {
		await call("frappe.ai.workspace.respond", { kind: item.kind, name: item.name, action })
		toast.success(`${action}: ${item.title || item.text}`)
		refreshed.value++
	} catch (error) {
		toast.error(errorText(error))
	} finally {
		busy.value = null
	}
}
</script>
