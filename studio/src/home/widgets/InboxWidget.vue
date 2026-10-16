<template>
	<!-- on a Home the inbox holds only what its queues do not show, and stays away while that and the day's done are nothing -->
	<WidgetFrame v-if="!(onHome && data && !data.items.length && !data.done.length)" v-bind="$attrs" :widget="widget" :count="data?.items.length">
		<div v-if="!data" class="flex flex-col gap-2 p-3">
			<Skeleton v-for="i in 3" :key="i" class="h-4 w-full rounded" />
		</div>
		<template v-else>
			<p v-if="!data.items.length" class="flex items-center gap-2 px-3 py-2.5 text-sm text-ink-gray-5">
				<span class="lucide-check size-3.5" />Nothing waits on you.
			</p>
			<div class="max-h-[480px] overflow-y-auto">
				<InboxList :items="data.items" :done="data.done" />
			</div>
		</template>
	</WidgetFrame>
</template>

<script setup lang="ts">
import { Skeleton } from "frappe-ui"
import { ref, watch } from "vue"

import InboxList, { type InboxItem } from "../InboxList.vue"
import { type Widget, getWidget, refreshed } from "../home"
import type { DoneEntry } from "./DoneList.vue"
import WidgetFrame from "./WidgetFrame.vue"

defineOptions({ inheritAttrs: false })
const props = defineProps<{ widget: Widget }>()

const data = ref<{ items: InboxItem[]; done: DoneEntry[] } | null>(null)
const onHome = !props.widget.space
async function load() {
	data.value = await getWidget<NonNullable<typeof data.value>>(props.widget).catch(() => ({ items: [], done: [] }))
}
watch(() => [props.widget.id, refreshed.value], load, { immediate: true })
</script>
