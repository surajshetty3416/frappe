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
			<div class="overflow-hidden rounded-6 border border-outline-gray-2">
				<div v-if="!inbox" class="flex flex-col gap-2 p-3">
					<Skeleton v-for="i in 5" :key="i" class="h-4 w-full rounded" />
				</div>
				<template v-else>
					<p v-if="!shown.length" class="flex items-center gap-2 px-3 py-3 text-sm text-ink-gray-5">
						<span class="lucide-check size-3.5" />Nothing waits on you here.
					</p>
					<InboxList :items="shown" :done="inbox.done" labelled />
				</template>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { Button, Skeleton, call } from "frappe-ui"
import { computed, ref, watch } from "vue"

import InboxList, { type InboxItem } from "./InboxList.vue"
import { inboxCount, openView, refreshed } from "./home"
import type { DoneEntry } from "./widgets/DoneList.vue"

const FILTERS = [
	{ label: "All", value: "all" },
	{ label: "Approvals", value: "approval" },
	{ label: "Assigned", value: "assignment" },
	{ label: "Mentions", value: "mention" },
] as const

openView.value = null
document.title = "Inbox"

const inbox = ref<{ items: InboxItem[]; done: DoneEntry[] } | null>(null)
async function load() {
	inbox.value = await call<NonNullable<typeof inbox.value>>("frappe.ai.workspace.get_inbox").catch(() => ({ items: [], done: [] }))
	inboxCount.value = inbox.value.items.length
}
watch(refreshed, load, { immediate: true })

const kind = ref<(typeof FILTERS)[number]["value"]>("all")
const shown = computed(() => (inbox.value?.items ?? []).filter((item) => kind.value === "all" || item.kind === kind.value))
const counts = computed(() => {
	const all: Record<string, number> = { all: inbox.value?.items.length ?? 0 }
	for (const item of inbox.value?.items ?? []) all[item.kind] = (all[item.kind] ?? 0) + 1
	return all
})
</script>
