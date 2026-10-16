<template>
	<WidgetFrame v-bind="$attrs" :widget="widget">
		<div v-if="!fields" class="flex flex-col gap-2 p-3">
			<Skeleton v-for="i in 2" :key="i" class="h-4 w-full rounded" />
		</div>
		<p v-else-if="!canCreate" class="px-3 py-2.5 text-sm text-ink-gray-5">You cannot create {{ widget.doctype }} records.</p>
		<!-- the fields side by side as the width allows, the button at the end of the last row -->
		<form v-else class="grid grid-cols-[repeat(auto-fit,minmax(140px,1fr))] items-end gap-2 p-3" @submit.prevent="submit">
			<label v-for="field in fields" :key="field.fieldname" class="flex min-w-0 flex-col gap-1">
				<span class="text-xs text-ink-gray-5">{{ field.label }}<span v-if="field.reqd" class="text-ink-red-4"> *</span></span>
				<RecordField :field="field" :model-value="values[field.fieldname]" @update:model-value="(value) => (values[field.fieldname] = value)" />
			</label>
			<Button variant="solid" type="submit" label="Create" :loading="saving" />
		</form>
	</WidgetFrame>
</template>

<script setup lang="ts">
import { Button, Skeleton, call, toast } from "frappe-ui"
import { reactive, ref, watch } from "vue"

import RecordField from "../../../data/src/components/RecordField.vue"
import { type Widget, getWidget, refreshed } from "../home"
import WidgetFrame from "./WidgetFrame.vue"
import { type FieldSpec, errorText } from "./format"

defineOptions({ inheritAttrs: false })
const props = defineProps<{ widget: Widget }>()

const fields = ref<FieldSpec[] | null>(null)
const canCreate = ref(false)
const values = reactive<Record<string, unknown>>({})

watch(
	() => props.widget.id,
	async () => {
		const data = await getWidget<{ fields: FieldSpec[]; can_create: boolean }>(props.widget.id)
		fields.value = data.fields
		canCreate.value = data.can_create
	},
	{ immediate: true }
)

const saving = ref(false)
async function submit() {
	saving.value = true
	try {
		const made = await call("frappe.ai.workspace.create", { widget: props.widget.id, values })
		toast.success(`Created ${made.title}`)
		Object.keys(values).forEach((key) => delete values[key])
		refreshed.value++
	} catch (error) {
		toast.error(errorText(error))
	} finally {
		saving.value = false
	}
}
</script>
