<template>
	<WidgetFrame v-bind="$attrs" :widget="widget" :count="data?.count">
		<div v-if="widget.search" class="border-b border-outline-gray-1 p-2">
			<TextInput v-model="txt" size="sm" variant="ghost" :placeholder="`Search ${widgetTitle(widget).toLowerCase()}`">
				<template #prefix><span class="lucide-search size-3.5 text-ink-gray-5" /></template>
			</TextInput>
		</div>
		<div class="h-[360px] overflow-y-auto">
			<div v-if="!data" class="flex h-full items-center justify-center">
				<LoadingIndicator class="size-4 text-ink-gray-5" />
			</div>
			<p v-else-if="data.denied" class="p-4 text-base text-ink-gray-5">You cannot see {{ widget.doctype }} records.</p>
			<p v-else-if="!data.rows.length" class="p-4 text-base text-ink-gray-5">{{ txt ? "Nothing matches." : "Nothing waits here. All done." }}</p>
			<ul v-else class="divide-y divide-outline-gray-1">
				<li
					v-for="row in data.rows"
					:key="row.name"
					class="group flex cursor-pointer items-center gap-3 px-3 py-2 hover:bg-surface-gray-1"
					@click="showRecord(widget.doctype!, row.name, row._title)"
				>
					<div class="min-w-0 flex-1">
						<p class="truncate text-base text-ink-gray-8">{{ row._title }}</p>
						<p class="truncate text-sm text-ink-gray-5">
							<template v-for="(field, i) in data.fields" :key="field.fieldname">
								<span v-if="i" class="text-ink-gray-3"> · </span>{{ shown(field, row[field.fieldname]) }}
							</template>
						</p>
					</div>
					<div class="flex shrink-0 items-center gap-1" @click.stop>
						<Button
							v-for="action in row._actions"
							:key="action"
							size="sm"
							:variant="action === row._actions[0] ? 'subtle' : 'ghost'"
							:label="widget.actions![action].label"
							:loading="busy === `${row.name}/${action}`"
							@click="run(row, action)"
						/>
					</div>
				</li>
			</ul>
		</div>
	</WidgetFrame>
</template>

<script setup lang="ts">
import { watchDebounced } from "@vueuse/core"
import { Button, LoadingIndicator, TextInput, call, toast } from "frappe-ui"
import { ref, watch } from "vue"

import { type Widget, getWidget, refreshed, showRecord, widgetTitle } from "../home"
import WidgetFrame from "./WidgetFrame.vue"
import { type FieldSpec, errorText, shown } from "./format"

type Row = Record<string, unknown> & { name: string; _title: string; _actions: number[] }

defineOptions({ inheritAttrs: false })
const props = defineProps<{ widget: Widget }>()

const data = ref<{ rows: Row[]; count: number; fields: FieldSpec[]; denied?: boolean } | null>(null)
const txt = ref("")

async function load() {
	data.value = await getWidget<NonNullable<typeof data.value>>(props.widget.id, txt.value || undefined).catch((error) => {
		toast.error(errorText(error))
		return { rows: [], count: 0, fields: [] }
	})
}
watch(() => [props.widget.id, refreshed.value], load, { immediate: true })
watchDebounced(txt, load, { debounce: 250 })

const busy = ref<string | null>(null)
async function run(row: Row, action: number) {
	busy.value = `${row.name}/${action}`
	try {
		await call("frappe.ai.workspace.act", { widget: props.widget.id, action, name: row.name })
		toast.success(`${props.widget.actions![action].label}: ${row._title}`)
		refreshed.value++
	} catch (error) {
		toast.error(errorText(error))
	} finally {
		busy.value = null
	}
}
</script>
