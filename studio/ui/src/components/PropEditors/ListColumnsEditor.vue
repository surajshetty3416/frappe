<template>
	<div class="flex w-full flex-col gap-2">
		<ArrayInput
			:modelValue="columnWidths"
			:label="Array.isArray(columns) || !label ? label : `${label} · ${breakpointKey === 'md' ? 'from 768px' : 'phone'}`"
			addLabel="Add Column"
			newItemValue="8rem"
			@update:modelValue="setColumnWidths"
			@add="addCells"
			@remove="removeCells"
			@move="moveCells"
		/>

		<!-- the tree drifted from `columns` (hand-edited header/rows) -->
		<div v-if="mismatch.length" class="flex items-center gap-1.5 text-xs text-ink-amber-5">
			<span class="size-[5px] flex-none rounded-full bg-surface-amber-5"></span>
			{{ mismatch.join(" · ") }}
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed } from "vue"
import ArrayInput from "@ui/components/ArrayInput.vue"
import Block from "@ui/utils/block"
import useCanvasStore from "@ui/stores/canvasStore"
import { listCell, listHeaderCell } from "@ui/utils/blockTemplate/familyTemplates"

const props = defineProps<{ block: Block; label?: string }>()

const canvasStore = useCanvasStore()

const HEADER_CELL_NAMES = ["ListHeaderCell", "ListHeaderCellSort"]

// `columns` is one template, or one per breakpoint (`{ base, md }`): the phone view edits `base`,
// the wider views `md`, which falls back to `base` as the CSS does
const columns = computed(() => props.block.getProp("columns"))
const breakpointKey = computed(() => (canvasStore.activeCanvas?.activeBreakpoint === "mobile" ? "base" : "md"))

const columnWidths = computed<string[]>(() => {
	const value = columns.value
	if (Array.isArray(value)) return value
	if (!value || typeof value !== "object") return []
	return value[breakpointKey.value] ?? value.base ?? []
})

function setColumnWidths(next: string[]) {
	const value = columns.value
	if (Array.isArray(value) || !value || typeof value !== "object") return props.block.setProp("columns", next)
	props.block.setProp("columns", { ...value, [breakpointKey.value]: next })
}

// the phone's template holds only the columns it keeps, so its edits leave the cells alone
const editsCells = computed(() => Array.isArray(columns.value) || breakpointKey.value === "md")

// A column lives in three places — a width entry in `columns`, a header cell, and a cell
// in every row template — kept in step positionally so header and rows never drift.
// ArrayInput edits the widths; `add`/`remove` mirror the operation onto the cells.
function addCells() {
	if (!editsCells.value) return
	headerBlock.value?.addChild(listHeaderCell(`Column ${columnWidths.value.length}`), null, false)
	rowBlocks.value.forEach((row) => row.addChild(listCell("—"), null, false))
}

function removeCells(index: number) {
	if (!editsCells.value) return
	removeCellAt(headerBlock.value, HEADER_CELL_NAMES, index)
	rowBlocks.value.forEach((row) => removeCellAt(row, ["ListCell"], index))
}

function moveCells({ from, to }: { from: number; to: number }) {
	if (!editsCells.value) return
	moveCellAt(headerBlock.value, HEADER_CELL_NAMES, from, to)
	rowBlocks.value.forEach((row) => moveCellAt(row, ["ListCell"], from, to))
}

const mismatch = computed(() => {
	const expected = columnWidths.value.length
	const problems: string[] = []
	if (editsCells.value && headerBlock.value) {
		const count = cellsOf(headerBlock.value, HEADER_CELL_NAMES).length
		if (count !== expected) problems.push(`Header has ${count} of ${expected} cells`)
	}
	const offRows = editsCells.value ? rowBlocks.value.filter((row) => cellsOf(row, ["ListCell"]).length !== expected) : []
	if (offRows.length) {
		problems.push(`${offRows.length} row${offRows.length === 1 ? "" : "s"} with a mismatched cell count`)
	}
	const invalid = columnWidths.value.filter((width) => !isValidWidth(width))
	if (invalid.length) {
		problems.push(
			`Invalid width${invalid.length === 1 ? "" : "s"}: ${invalid.map((width) => `"${width}"`).join(", ")}`,
		)
	}
	return problems
})

function isValidWidth(width: string) {
	// dynamic bindings resolve at render time — nothing to validate here
	if (typeof width !== "string" || width.includes("{{")) return true
	return CSS.supports("grid-template-columns", width)
}

const headerBlock = computed(
	() => props.block.children.find((child) => child.componentName === "ListHeader") || null,
)

// ListRow templates under ListRows — as direct children or slot content, including
// rows nested inside ListGroups.
const rowBlocks = computed(() => {
	const rows: Block[] = []
	const collect = (blocks: Block[]) => {
		blocks.forEach((child) => {
			if (child.componentName === "ListRow") rows.push(child)
			if (child.componentName === "ListGroup") collect(child.getChildrenAndSlotContent())
		})
	}
	const listRows = props.block.children.find((child) => child.componentName === "ListRows")
	if (listRows) collect(listRows.getChildrenAndSlotContent())
	return rows
})

function cellsOf(parent: Block, names: string[]): Block[] {
	return parent.getChildrenAndSlotContent().filter((child) => names.includes(child.componentName))
}

function removeCellAt(parent: Block | null, names: string[], index: number) {
	if (!parent) return
	const cell = cellsOf(parent, names)[index]
	if (cell) parent.removeChild(cell)
}

function moveCellAt(parent: Block | null, names: string[], from: number, to: number) {
	if (!parent) return
	const cell = cellsOf(parent, names)[from]
	if (!cell) return
	parent.removeChild(cell)
	const remaining = cellsOf(parent, names)
	const anchor = remaining[to]
	const lastCell = remaining.at(-1)
	const index = anchor
		? parent.getChildIndex(anchor)
		: lastCell
			? (parent.getChildIndex(lastCell) ?? -1) + 1
			: undefined
	parent.addChild(cell, index, false)
}
</script>
