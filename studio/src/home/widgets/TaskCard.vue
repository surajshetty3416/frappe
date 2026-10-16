<template>
	<!-- a row opened up: who it is from, what it says, and the ways to finish it -->
	<div class="flex flex-col gap-3 border-t border-outline-gray-1 bg-surface-gray-1 px-3 py-3" @click.stop>
		<div v-if="!task" class="flex flex-col gap-2">
			<Skeleton v-for="i in 3" :key="i" class="h-4 w-full rounded" />
		</div>
		<template v-else>
			<div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
				<span class="flex gap-1 text-ink-gray-8"><span class="text-ink-gray-5">From</span>{{ task.who }}</span>
				<span v-for="fact in task.facts" :key="fact.label" class="flex gap-1 text-ink-gray-8">
					<span class="text-ink-gray-5">{{ fact.label }}</span>{{ fact.value }}
				</span>
				<span class="text-ink-gray-5">{{ dayjs(task.created).fromNow() }}</span>
				<Button class="ml-auto" variant="ghost" size="sm" icon-right="lucide-arrow-up-right" label="Open full form" :href="task.url" />
			</div>
			<p v-if="task.text" class="line-clamp-4 whitespace-pre-line text-sm text-ink-gray-7">{{ task.text }}</p>
			<ul v-if="task.timeline.length" class="flex flex-col gap-2 border-l border-outline-gray-2 pl-3">
				<li v-for="(entry, i) in task.timeline" :key="i" class="flex flex-col gap-0.5 text-sm">
					<span class="text-xs text-ink-gray-5">
						<span class="text-ink-gray-7">{{ entry.who }}</span>
						{{ entry.kind === "email" ? "emailed" : "commented" }} · {{ dayjs(entry.when).fromNow() }}
					</span>
					<span class="line-clamp-3 whitespace-pre-line text-ink-gray-7">{{ entry.text }}</span>
				</li>
			</ul>

			<div v-if="actions.length" class="flex flex-col gap-3 rounded-4 border border-outline-gray-2 bg-surface-base p-3">
				<div class="flex flex-wrap gap-1.5">
					<Button
						v-for="(action, i) in actions"
						:key="action.label"
						size="sm"
						:variant="chosen === i ? 'solid' : 'subtle'"
						:label="action.label"
						@click="chosen = chosen === i ? null : i"
					/>
				</div>
				<template v-if="current">
					<ol class="flex flex-col gap-0.5 text-sm text-ink-gray-6">
						<li v-for="(step, i) in current.steps" :key="step" class="flex gap-2">
							<span class="w-3 shrink-0 tabular-nums text-ink-gray-4">{{ i + 1 }}</span>{{ step }}
						</li>
					</ol>
					<label v-if="current.replyTo" class="flex flex-col gap-1.5">
						<span class="text-xs text-ink-gray-5">Reply to {{ current.replyTo }}</span>
						<Textarea v-model="reply" :rows="4" placeholder="Write your reply…" />
					</label>
					<label v-for="field in current.fields" :key="field.fieldname" class="flex flex-col gap-1.5">
						<span class="text-xs text-ink-gray-5">{{ field.label }}<span class="text-ink-red-4"> *</span></span>
						<RecordField :field="field" :model-value="values[field.fieldname]" @update:model-value="(value) => (values[field.fieldname] = value)" />
					</label>
					<label v-if="current.comment" class="flex flex-col gap-1.5">
						<span class="text-xs text-ink-gray-5">
							{{ current.comment === "required" ? "Why" : "Note" }}<span v-if="current.comment === 'required'" class="text-ink-red-4"> *</span>
						</span>
						<Textarea v-model="comment" :rows="2" :placeholder="current.comment === 'required' ? 'Say why, for the record' : 'Optional'" />
					</label>
					<div class="flex justify-end gap-2">
						<Button variant="ghost" size="sm" label="Cancel" @click="chosen = null" />
						<Button variant="solid" size="sm" :label="current.label" :loading="busy" :disabled="!ready" @click="submit" />
					</div>
				</template>
			</div>
		</template>
	</div>
</template>

<script setup lang="ts">
import { Button, Skeleton, Textarea, call, dayjs, toast } from "frappe-ui"
import { computed, reactive, ref, watch } from "vue"

import RecordField from "../../../data/src/components/RecordField.vue"
import { type FieldSpec, errorText } from "./format"

export interface TaskAction {
	label: string
	steps: string[]
	fields?: FieldSpec[]
	comment?: "optional" | "required" | null
	// the address a reply goes to, when the action replies first
	replyTo?: string | null
}

export interface TaskInput {
	values: Record<string, unknown>
	comment: string
	reply: string
}

interface Task {
	title: string
	url: string
	who: string
	created: string
	facts: { label: string; value: string }[]
	text: string | null
	timeline: { who: string; when: string; text: string; kind: "comment" | "email" }[]
}

const props = defineProps<{
	doctype: string
	name: string
	actions: TaskAction[]
	choose?: number | null
	perform: (action: number, input: TaskInput) => Promise<void>
}>()

const task = ref<Task | null>(null)
watch(
	() => [props.doctype, props.name],
	async () => {
		task.value = await call<Task>("frappe.ai.workspace.get_task", { doctype: props.doctype, name: props.name }).catch((error) => {
			toast.error(errorText(error))
			return null
		})
	},
	{ immediate: true }
)

const chosen = ref<number | null>(props.choose ?? null)
const current = computed(() => (chosen.value === null ? null : props.actions[chosen.value]))
const values = reactive<Record<string, unknown>>({})
const comment = ref("")
const reply = ref("")
watch(chosen, () => {
	Object.keys(values).forEach((key) => delete values[key])
	comment.value = ""
})

const ready = computed(() => {
	const action = current.value
	if (!action) return false
	if (action.replyTo && !reply.value.trim()) return false
	if (action.comment === "required" && !comment.value.trim()) return false
	return (action.fields ?? []).every((field) => values[field.fieldname] !== undefined && values[field.fieldname] !== "")
})

const busy = ref(false)
async function submit() {
	if (chosen.value === null) return
	busy.value = true
	try {
		await props.perform(chosen.value, { values: { ...values }, comment: comment.value, reply: reply.value })
	} finally {
		busy.value = false
	}
}
</script>
