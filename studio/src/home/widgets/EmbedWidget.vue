<template>
	<WidgetFrame v-bind="$attrs" :widget="{ ...widget, title: widget.title || view?.title || null }">
		<template #header>
			<Button v-if="view" variant="ghost" size="sm" icon="lucide-maximize-2" tooltip="Open" :route="viewRoute(view)" />
		</template>
		<div :class="view?.view ? 'h-[480px]' : ''">
			<iframe v-if="view?.view" :src="view.view" :title="view.title" class="size-full border-0" />
			<p v-else-if="loaded" class="px-3 py-2.5 text-sm text-ink-gray-5">
				{{ view ? `This ${view.label.toLowerCase()} is not published yet.` : "You cannot open what this shows." }}
			</p>
		</div>
	</WidgetFrame>
</template>

<script setup lang="ts">
import { Button } from "frappe-ui"
import { ref, watch } from "vue"

import { type View, type Widget, getWidget, viewRoute } from "../home"
import WidgetFrame from "./WidgetFrame.vue"

defineOptions({ inheritAttrs: false })
const props = defineProps<{ widget: Widget }>()

const view = ref<View | null>(null)
const loaded = ref(false)
watch(
	() => props.widget.id,
	async () => {
		view.value = (await getWidget<{ view: View | null }>(props.widget.id).catch(() => ({ view: null }))).view
		loaded.value = true
	},
	{ immediate: true }
)
</script>
