<template>
	<div
		v-if="data.doctype.core"
		class="relative flex h-10 w-[240px] cursor-pointer items-center gap-2 rounded-6 border border-dashed border-outline-gray-3 bg-surface-base px-3 hover:border-outline-gray-4"
	>
		<Handle id="in" type="target" :position="Position.Left" :class="HANDLE" />
		<span class="lucide-box size-4 shrink-0 text-ink-gray-5" />
		<span class="min-w-0 flex-1 truncate text-sm font-medium text-ink-gray-7">{{ data.doctype.name }}</span>
		<span class="shrink-0 text-xs text-ink-gray-5">Core</span>
	</div>
	<div v-else class="w-[260px] cursor-pointer rounded-6 border border-outline-gray-2 bg-surface-base hover:border-outline-gray-4">
		<div class="relative flex h-10 items-center gap-2 border-b border-outline-gray-1 px-3">
			<Handle id="in" type="target" :position="Position.Left" :class="HANDLE" />
			<span class="lucide-table-2 size-4 shrink-0 text-ink-gray-6" />
			<span class="min-w-0 flex-1 truncate text-sm font-medium text-ink-gray-8">{{ data.doctype.name }}</span>
			<span v-if="data.doctype.count !== null" class="shrink-0 text-xs tabular-nums text-ink-gray-5">{{ data.doctype.count.toLocaleString() }}</span>
		</div>
		<div class="py-1">
			<FieldRow v-for="field in rows(data.doctype)" :key="field.fieldname" :field="field" :handle="field.fieldname" />
		</div>
		<div v-for="child in data.children" :key="child.name" class="mx-2 mb-2 rounded-4 border border-outline-gray-1 bg-surface-gray-1">
			<div class="flex h-7 items-center gap-2 px-2">
				<span class="lucide-table size-3.5 shrink-0 text-ink-gray-5" />
				<span class="truncate text-xs font-medium text-ink-gray-7">{{ child.name }}</span>
			</div>
			<div class="pb-1">
				<FieldRow v-for="field in rows(child)" :key="field.fieldname" :field="field" :handle="`${child.name}.${field.fieldname}`" compact />
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { Handle, Position } from "@vue-flow/core"
import { defineComponent, h } from "vue"

import type { SchemaNode } from "../api"
import { TABLE_TYPES, fieldIcon } from "../fields"

defineProps<{ data: { doctype: SchemaNode; children: SchemaNode[] } }>()

const HANDLE = "!size-1.5 !min-h-0 !min-w-0 !border-0 !bg-outline-gray-4"

// tables show as the nested box below, not as a row
const rows = (doctype: SchemaNode) => doctype.fields.filter((field) => !TABLE_TYPES.has(field.fieldtype))

type Field = SchemaNode["fields"][number]

const FieldRow = defineComponent({
	props: { field: { type: Object as () => Field, required: true }, handle: { type: String, required: true }, compact: Boolean },
	setup(props) {
		return () =>
			h("div", { class: ["relative flex items-center gap-2 px-3", props.compact ? "h-6 px-2" : "h-7"] }, [
				h("span", { class: [fieldIcon(props.field.fieldtype), "size-3.5 shrink-0 text-ink-gray-4"] }),
				h("span", { class: "min-w-0 flex-1 truncate text-xs text-ink-gray-7" }, props.field.label || props.field.fieldname),
				h(
					"span",
					{ class: "max-w-[45%] shrink-0 truncate text-xs text-ink-gray-5" },
					props.field.fieldtype === "Link" ? `→ ${props.field.options}` : props.field.fieldtype
				),
				props.field.fieldtype === "Link"
					? h(Handle, { id: props.handle, type: "source", position: Position.Right, class: HANDLE })
					: null,
			])
	},
})
</script>
