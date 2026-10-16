<template>
	<WidgetFrame v-bind="$attrs" :widget="widget" :count="items?.length">
		<div class="h-[360px] overflow-y-auto">
			<div v-if="!items" class="flex h-full items-center justify-center">
				<LoadingIndicator class="size-4 text-ink-gray-5" />
			</div>
			<p v-else-if="!items.length" class="p-4 text-base text-ink-gray-5">Nothing waits on you. Inbox zero.</p>
			<ul v-else class="divide-y divide-outline-gray-1">
				<li
					v-for="item in items"
					:key="`${item.kind}/${item.name}`"
					class="flex items-center gap-3 px-3 py-2"
					:class="item.doctype ? 'cursor-pointer hover:bg-surface-gray-1' : ''"
					@click="item.doctype && item.record && showRecord(item.doctype, item.record, item.title ?? undefined)"
				>
					<span
						:class="item.kind === 'approval' ? 'lucide-stamp text-ink-amber-6' : 'lucide-circle-dot text-ink-blue-6'"
						class="size-4 shrink-0"
					/>
					<div class="min-w-0 flex-1">
						<p class="truncate text-base text-ink-gray-8">{{ item.title || item.text }}</p>
						<p class="truncate text-sm text-ink-gray-5">
							{{ item.title ? item.text : item.doctype || "Task" }}
							<template v-if="item.due"> · due {{ dayjs(item.due).format("D MMM") }}</template>
						</p>
					</div>
					<div class="flex shrink-0 items-center gap-1" @click.stop>
						<Button
							v-for="(action, i) in item.actions"
							:key="action"
							size="sm"
							:variant="i === 0 ? 'subtle' : 'ghost'"
							:label="action"
							:loading="busy === `${item.name}/${action}`"
							@click="respond(item, action)"
						/>
					</div>
				</li>
			</ul>
		</div>
	</WidgetFrame>
</template>

<script setup lang="ts">
import { Button, LoadingIndicator, call, dayjs, toast } from "frappe-ui"
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
