<template>
	<WidgetFrame v-bind="$attrs" :widget="widget" :count="items?.length">
		<div v-if="!items" class="flex flex-col gap-2 p-3">
			<Skeleton v-for="i in 3" :key="i" class="h-4 w-full rounded" />
		</div>
		<p v-else-if="!items.length" class="flex items-center gap-2 px-3 py-2.5 text-sm text-ink-gray-5">
			<span class="lucide-check size-3.5" />Nothing waits on you.
		</p>
		<ul v-else class="max-h-[384px] divide-y divide-outline-gray-1 overflow-y-auto [scrollbar-gutter:stable]">
			<li
				v-for="item in items"
				:key="`${item.kind}/${item.name}`"
				class="group flex h-9 items-center gap-2.5 px-3 transition-colors duration-75"
				:class="item.doctype ? 'cursor-pointer hover:bg-surface-gray-1' : ''"
				@click="item.doctype && item.record && showRecord(item.doctype, item.record, item.title ?? undefined)"
			>
				<!-- an approval waits on a decision, an assignment on the person -->
				<span
					class="size-1.5 shrink-0 rounded-full"
					:class="item.kind === 'approval' ? 'bg-surface-amber-5' : 'bg-surface-blue-6'"
					:title="item.kind === 'approval' ? 'Approval' : 'Assignment'"
				/>
				<span class="min-w-0 shrink truncate text-sm text-ink-gray-8">{{ item.title || item.text }}</span>
				<span class="min-w-0 flex-1 truncate text-sm text-ink-gray-5">
					{{ item.title ? item.text : item.doctype || "Task" }}<template v-if="item.due"> · due {{ dayjs(item.due).format("D MMM") }}</template>
				</span>
				<span class="flex shrink-0 items-center gap-1" @click.stop>
					<Button
						v-for="(action, i) in item.actions"
						:key="action"
						size="sm"
						:variant="i === 0 ? 'subtle' : 'ghost'"
						:class="i === 0 ? '' : 'opacity-0 group-hover:opacity-100 focus-visible:opacity-100'"
						:label="action"
						:loading="busy === `${item.name}/${action}`"
						@click="respond(item, action)"
					/>
				</span>
			</li>
		</ul>
	</WidgetFrame>
</template>

<script setup lang="ts">
import { Button, Skeleton, call, dayjs, toast } from "frappe-ui"
import { ref, watch } from "vue"

import { type Widget, getWidget, refreshed, showRecord } from "../home"
import WidgetFrame from "./WidgetFrame.vue"
import { errorText } from "./format"

interface Item {
	kind: "assignment" | "approval"
	name: string
	text: string
	doctype: string | null
	record: string | null
	title: string | null
	due?: string
	actions: string[]
}

defineOptions({ inheritAttrs: false })
const props = defineProps<{ widget: Widget }>()

const items = ref<Item[] | null>(null)
async function load() {
	items.value = (await getWidget<{ items: Item[] }>(props.widget.id).catch(() => ({ items: [] }))).items
}
watch(() => [props.widget.id, refreshed.value], load, { immediate: true })

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
