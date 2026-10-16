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
		<ul v-else class="max-h-[480px] divide-y divide-outline-gray-1 overflow-y-auto">
			<li v-for="row in data.rows" :key="row.name">
				<div
					class="flex h-9 cursor-pointer items-center gap-3 px-3 transition-colors duration-75 hover:bg-surface-gray-1"
					:class="open?.name === row.name ? 'bg-surface-gray-1' : ''"
					@click="open = open?.name === row.name ? null : { name: row.name, choose: null }"
				>
					<span class="min-w-0 shrink truncate text-sm text-ink-gray-8">{{ row._title }}</span>
					<span class="min-w-0 flex-1 truncate text-sm tabular-nums text-ink-gray-5">
						<template v-for="(field, i) in details(row)" :key="field.fieldname">
							<span v-if="i" class="text-ink-gray-3"> · </span>{{ shown(field, row[field.fieldname]) }}
						</template>
					</span>
					<!-- what the person did to it today, while it still waits here -->
					<span v-if="row._did" class="flex min-w-0 shrink items-center gap-1 truncate text-xs text-ink-gray-5" :title="row._did.what">
						<span class="lucide-check size-3 shrink-0 text-ink-green-5" />{{ row._did.what }} · {{ dayjs(row._did.when).fromNow() }}
					</span>
					<!-- the first thing to do: done in place when it needs nothing, else opened to ask -->
					<Button
						v-if="row._actions.length"
						size="sm"
						variant="subtle"
						:label="data.actions[row._actions[0]].label"
						:icon-right="asks(row._actions[0]) ? 'lucide-chevron-down' : undefined"
						:loading="busy === row.name"
						@click.stop="start(row)"
					/>
				</div>
				<TaskCard
					v-if="open?.name === row.name"
					:doctype="widget.doctype!"
					:name="row.name"
					:actions="row._actions.map((action) => card(row, action))"
					:choose="open.choose"
					:perform="(i, input) => run(row, row._actions[i], input)"
				/>
			</li>
		</ul>
		<DoneList v-if="data?.done?.length" :entries="data.done" :fresh="fresh" :undoing="undoing" @undo="undo" />
	</WidgetFrame>
</template>

<script setup lang="ts">
import { watchDebounced } from "@vueuse/core"
import { Button, Skeleton, TextInput, call, dayjs, toast } from "frappe-ui"
import { ref, watch } from "vue"

import { type Widget, getWidget, refreshed } from "../home"
import DoneList, { type DoneEntry } from "./DoneList.vue"
import TaskCard, { type TaskAction, type TaskInput } from "./TaskCard.vue"
import WidgetFrame from "./WidgetFrame.vue"
import { type FieldSpec, errorText, shown } from "./format"

type Row = Record<string, unknown> & {
	name: string
	_title: string
	_actions: number[]
	_did: { what: string; when: string } | null
}
interface Action {
	label: string
	steps: string[]
	fields: FieldSpec[]
	comment: "optional" | "required" | null
	reply: string | null
}

defineOptions({ inheritAttrs: false })
const props = defineProps<{ widget: Widget }>()

const data = ref<{
	rows: Row[]
	count: number
	fields: FieldSpec[]
	actions: Action[]
	done: DoneEntry[]
	denied?: boolean
} | null>(null)
const txt = ref("")

// a row's details, less any that only repeats its title
const details = (row: Row) => data.value!.fields.filter((field) => row[field.fieldname] !== row._title)

async function load() {
	data.value = await getWidget<NonNullable<typeof data.value>>(props.widget, txt.value || undefined).catch((error) => {
		toast.error(errorText(error))
		return { rows: [], count: 0, fields: [], actions: [], done: [] }
	})
}
watch(() => [props.widget.id, refreshed.value], load, { immediate: true })
watchDebounced(txt, load, { debounce: 250 })

const asks = (action: number) => {
	const spec = data.value!.actions[action]
	return Boolean(spec.fields.length || spec.comment || spec.reply)
}
const card = (row: Row, action: number): TaskAction => {
	const spec = data.value!.actions[action]
	return { ...spec, replyTo: spec.reply ? String(row[spec.reply] ?? "") || null : null }
}

const open = ref<{ name: string; choose: number | null } | null>(null)
function start(row: Row) {
	if (asks(row._actions[0])) open.value = { name: row.name, choose: 0 }
	else run(row, row._actions[0], { values: {}, comment: "", reply: "" })
}

const busy = ref<string | null>(null)
const fresh = ref<string | null>(null)
async function run(row: Row, action: number, input: TaskInput) {
	busy.value = row.name
	try {
		const done = await call<{ undo: boolean }>("frappe.ai.workspace.act", {
			widget: props.widget.id,
			action,
			name: row.name,
			space: props.widget.space,
			values: input.values,
			comment: input.comment,
			reply: input.reply,
		})
		open.value = null
		fresh.value = row.name
		toast.success(`${data.value!.actions[action].label}: ${row._title}`, {
			action: done.undo ? { label: "Undo", onClick: () => undo({ name: row.name } as DoneEntry) } : undefined,
		})
		refreshed.value++
	} catch (error) {
		toast.error(errorText(error))
	} finally {
		busy.value = null
	}
}

const undoing = ref<string | null>(null)
async function undo(entry: DoneEntry) {
	undoing.value = entry.name
	try {
		await call("frappe.ai.workspace.undo", { widget: props.widget.id, name: entry.name, space: props.widget.space })
		fresh.value = null
		refreshed.value++
	} catch (error) {
		toast.error(errorText(error))
	} finally {
		undoing.value = null
	}
}
</script>
