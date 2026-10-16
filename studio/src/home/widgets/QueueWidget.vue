<template>
	<WidgetFrame v-bind="$attrs" :widget="widget" :count="data?.count">
		<template #header>
			<TextInput v-if="widget.search" v-model="txt" class="w-44" size="sm" variant="subtle" placeholder="Search">
				<template #prefix><span class="lucide-search size-3.5 text-ink-gray-4" /></template>
			</TextInput>
		</template>
		<div v-if="!data" class="flex flex-col gap-2 p-3">
			<Skeleton v-for="i in 3" :key="i" class="h-4 w-full rounded" />
		</div>
		<p v-else-if="data.denied" class="px-3 py-2.5 text-sm text-ink-gray-5">You cannot see {{ widget.doctype }} records.</p>
		<p v-else-if="!data.rows.length" class="flex items-center gap-2 px-3 py-2.5 text-sm text-ink-gray-5">
			<span class="lucide-check size-3.5" />{{ txt ? "Nothing matches." : "All clear." }}
		</p>
		<ul v-else class="max-h-[384px] divide-y divide-outline-gray-1 overflow-y-auto">
			<li
				v-for="row in data.rows"
				:key="row.name"
				class="group flex h-9 cursor-pointer items-center gap-3 px-3 transition-colors duration-75 hover:bg-surface-gray-1"
				@click="showRecord(widget.doctype!, row.name, row._title)"
			>
				<span class="min-w-0 shrink truncate text-sm text-ink-gray-8">{{ row._title }}</span>
				<span class="min-w-0 flex-1 truncate text-sm tabular-nums text-ink-gray-5">
					<template v-for="(field, i) in details(row)" :key="field.fieldname">
						<span v-if="i" class="text-ink-gray-3"> · </span>{{ shown(field, row[field.fieldname]) }}
					</template>
				</span>
				<span class="flex shrink-0 items-center gap-1" @click.stop>
					<Button
						v-for="(action, i) in row._actions"
						:key="action"
						size="sm"
						:variant="i === 0 ? 'subtle' : 'ghost'"
						:class="i === 0 ? '' : 'opacity-0 group-hover:opacity-100 focus-visible:opacity-100'"
						:label="widget.actions![action].label"
						:loading="busy === `${row.name}/${action}`"
						@click="run(row, action)"
					/>
				</span>
			</li>
		</ul>
	</WidgetFrame>
</template>

<script setup lang="ts">
import { watchDebounced } from "@vueuse/core"
import { Button, Skeleton, TextInput, call, toast } from "frappe-ui"
import { ref, watch } from "vue"

import { type Widget, getWidget, refreshed, showRecord } from "../home"
import WidgetFrame from "./WidgetFrame.vue"
import { type FieldSpec, errorText, shown } from "./format"

type Row = Record<string, unknown> & { name: string; _title: string; _actions: number[] }

defineOptions({ inheritAttrs: false })
const props = defineProps<{ widget: Widget }>()

const data = ref<{ rows: Row[]; count: number; fields: FieldSpec[]; denied?: boolean } | null>(null)
const txt = ref("")

// a row's details, less any that only repeats its title
const details = (row: Row) => data.value!.fields.filter((field) => row[field.fieldname] !== row._title)

async function load() {
	data.value = await getWidget<NonNullable<typeof data.value>>(props.widget, txt.value || undefined).catch((error) => {
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
		await call("frappe.ai.workspace.act", { widget: props.widget.id, action, name: row.name, space: props.widget.space })
		toast.success(`${props.widget.actions![action].label}: ${row._title}`)
		refreshed.value++
	} catch (error) {
		toast.error(errorText(error))
	} finally {
		busy.value = null
	}
}
</script>
