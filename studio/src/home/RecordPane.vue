<template>
	<div class="flex flex-col">
		<div v-if="!record" class="flex h-24 items-center justify-center">
			<LoadingIndicator class="size-4 text-ink-gray-5" />
		</div>
		<template v-else>
			<div class="flex flex-col gap-2 border-b border-outline-gray-1 p-4">
				<div class="flex items-center justify-between gap-2">
					<p class="truncate text-sm text-ink-gray-5">{{ record.doctype }} · {{ record.name }}</p>
					<Button variant="ghost" size="sm" icon-right="lucide-arrow-up-right" label="Open full form" :href="record.url" />
				</div>
				<p class="text-lg font-medium text-ink-gray-9">{{ record.title }}</p>
				<div v-if="record.transitions.length" class="flex flex-wrap gap-1.5 pt-1">
					<Button
						v-for="(action, i) in record.transitions"
						:key="action"
						:variant="i === 0 ? 'solid' : 'subtle'"
						:label="action"
						:loading="busy === action"
						@click="transition(action)"
					/>
				</div>
			</div>
			<div class="flex flex-col gap-3 p-4">
				<label v-for="field in record.fields" :key="field.fieldname" class="flex flex-col gap-1">
					<span class="text-sm text-ink-gray-6">{{ field.label }}</span>
					<RecordField
						:field="field"
						:readonly="Boolean(field.read_only)"
						:model-value="record.values[field.fieldname]"
						@update:model-value="(value) => set(field.fieldname, value)"
					/>
				</label>
			</div>
		</template>
	</div>
</template>

<script setup lang="ts">
import { useDebounceFn } from "@vueuse/core"
import { Button, LoadingIndicator, call, toast } from "frappe-ui"
import { ref, watch } from "vue"

import RecordField from "../../data/src/components/RecordField.vue"
import { refreshed } from "./home"
import { type FieldSpec, errorText } from "./widgets/format"

interface Record {
	doctype: string
	name: string
	title: string
	url: string
	fields: FieldSpec[]
	values: { [field: string]: unknown }
	can_write: boolean
	transitions: string[]
}

const props = defineProps<{ doctype: string; name: string }>()

const record = ref<Record | null>(null)
async function load() {
	record.value = await call<Record>("frappe.ai.workspace.get_record", { doctype: props.doctype, name: props.name }).catch((error) => {
		toast.error(errorText(error))
		return null
	})
}
watch(() => [props.doctype, props.name], load, { immediate: true })

// each change saves a moment after the last keystroke, as one write
const changed: { [field: string]: unknown } = {}
const save = useDebounceFn(async () => {
	const values = { ...changed }
	Object.keys(changed).forEach((key) => delete changed[key])
	try {
		await call("frappe.client.set_value", { doctype: props.doctype, name: props.name, fieldname: values })
		refreshed.value++
	} catch (error) {
		toast.error(errorText(error))
		await load()
	}
}, 600)

function set(field: string, value: unknown) {
	if (!record.value) return
	record.value.values[field] = value
	changed[field] = value
	save()
}

const busy = ref<string | null>(null)
async function transition(action: string) {
	busy.value = action
	try {
		await call("frappe.ai.workspace.apply_transition", { doctype: props.doctype, name: props.name, action })
		toast.success(`${action}: ${record.value?.title}`)
		refreshed.value++
		await load()
	} catch (error) {
		toast.error(errorText(error))
	} finally {
		busy.value = null
	}
}
</script>
