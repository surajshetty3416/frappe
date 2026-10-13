<template>
	<div
		ref="host"
		class="relative h-full overflow-hidden"
		@mouseover.capture="onPointer"
		@mousemove.capture="onPointer"
		@mousedown.capture="onMouseDown"
		@click.capture="onClick"
		@dblclick.capture="onDoubleClick"
		@contextmenu.capture="onContextMenu"
		@mouseleave="hovered = null"
	>
		<slot />
		<div v-if="editor" data-layer="shell" class="pointer-events-none absolute inset-0">
			<div
				v-if="hoverBox && hovered?.id !== selected?.id"
				class="absolute rounded-[2px] border border-outline-blue-4"
				:style="boxStyle(hoverBox)"
			/>
			<div
				v-if="selectBox"
				class="absolute rounded-[2px] border-2 border-outline-blue-5"
				:style="boxStyle(selectBox, 1)"
			/>
		</div>
		<div
			v-if="editor && selected && selectBox && !editing"
			ref="toolbar"
			data-selection-ui
			data-layer="shell"
			class="absolute z-10 flex h-9 items-center gap-0.5 rounded-xl border border-outline-gray-2 bg-surface-base p-1 shadow-lg"
			:style="toolbarStyle"
		>
			<span class="flex max-w-[160px] items-center gap-1.5 px-1.5 text-sm text-ink-gray-6">
				<span :class="selected.icon" class="size-4 shrink-0 text-ink-gray-5" />
				<span class="truncate">{{ selected.label }}</span>
			</span>
			<div class="mx-0.5 h-4 w-px bg-surface-gray-3" />
			<Button variant="ghost" icon="lucide-message-square-plus" tooltip="Comment" />
			<Button v-if="selected.hasText" variant="ghost" icon="lucide-type" tooltip="Edit text" @click="startEdit" />
			<template v-if="properties.length">
				<div class="mx-0.5 h-4 w-px bg-surface-gray-3" />
				<PropertyControl v-for="property in properties" :key="property.name" :property="property" />
			</template>
		</div>
	</div>
</template>

<script setup lang="ts">
import { Button } from "frappe-ui"
import { computed, onBeforeUnmount, onMounted, ref, shallowRef, watch } from "vue"

import type { ArtifactEditor, PreviewElement } from "../editor"
import PropertyControl from "./PropertyControl.vue"

const props = defineProps<{ editor: ArtifactEditor | null; artifact: string }>()

type Box = { top: number; left: number; width: number; height: number }

const host = ref<HTMLElement | null>(null)
const toolbar = ref<HTMLElement | null>(null)
const hovered = shallowRef<PreviewElement | null>(null)
const selected = shallowRef<PreviewElement | null>(null)
const hoverBox = ref<Box | null>(null)
const selectBox = ref<Box | null>(null)
const editing = ref<{ id: string; node: HTMLElement; original: string } | null>(null)

watch(
	() => [props.editor, props.artifact],
	() => {
		finishEdit(false)
		hovered.value = selected.value = null
	}
)

const properties = computed(() => (selected.value && props.editor ? props.editor.properties(selected.value.id).slice(0, 4) : []))

const ownsEvent = (event: Event) => {
	const target = event.target
	if (!props.editor || !(target instanceof Element)) return false
	if (target.closest("[data-selection-ui]")) return false
	return !editing.value?.node.contains(target)
}
const elementAt = (event: Event) => props.editor?.elementAt(event.target as Element) ?? null

// the preview stays a preview: its own hover, drag and selection never see the pointer
function onPointer(event: MouseEvent) {
	if (!ownsEvent(event)) return
	event.stopPropagation()
	const found = elementAt(event)
	if (found?.id !== hovered.value?.id) hovered.value = found
}
function onMouseDown(event: MouseEvent) {
	if (!ownsEvent(event)) return
	event.stopPropagation()
	event.preventDefault()
	if (editing.value) finishEdit(true)
}
function onClick(event: MouseEvent) {
	if (!ownsEvent(event)) return
	event.stopPropagation()
	event.preventDefault()
	selected.value = elementAt(event)
}
function onDoubleClick(event: MouseEvent) {
	if (!ownsEvent(event)) return
	event.stopPropagation()
	event.preventDefault()
	const found = elementAt(event)
	if (!found?.hasText) return
	selected.value = found
	startEdit()
}
function onContextMenu(event: MouseEvent) {
	if (!ownsEvent(event)) return
	event.stopPropagation()
	event.preventDefault()
}

function startEdit() {
	const element = selected.value
	const node = element && props.editor?.textNode(element.id)
	if (!element || !node) return
	editing.value = { id: element.id, node, original: node.innerHTML }
	node.contentEditable = "true"
	// a node laid out as `contents` has no box, and cannot take focus
	if (getComputedStyle(node).display === "contents") node.style.display = "block"
	node.style.userSelect = "text"
	node.style.outline = "none"
	node.style.cursor = "text"
	node.addEventListener("keydown", onEditKey)
	node.addEventListener("blur", onEditBlur)
	node.focus()
	const range = document.createRange()
	range.selectNodeContents(node)
	window.getSelection()?.removeAllRanges()
	window.getSelection()?.addRange(range)
}
function onEditKey(event: KeyboardEvent) {
	event.stopPropagation()
	if (event.key === "Enter" && !event.shiftKey) {
		event.preventDefault()
		finishEdit(true)
	} else if (event.key === "Escape") {
		event.preventDefault()
		finishEdit(false)
	}
}
const onEditBlur = () => finishEdit(true)
function finishEdit(save: boolean) {
	const edit = editing.value
	if (!edit) return
	editing.value = null
	const { node, id, original } = edit
	node.removeEventListener("keydown", onEditKey)
	node.removeEventListener("blur", onEditBlur)
	node.removeAttribute("contenteditable")
	node.style.userSelect = node.style.outline = node.style.cursor = ""
	if (node.style.display === "block") node.style.display = ""
	window.getSelection()?.removeAllRanges()
	if (save && node.innerHTML !== original) props.editor?.setText(id, node.innerHTML)
	else if (!save) node.innerHTML = original
}

// boxes follow their elements as the preview scrolls, zooms or reflows
function boxOf(element: PreviewElement | null): Box | null {
	const rect = element && props.editor?.elementRect(element.id)
	const origin = host.value?.getBoundingClientRect()
	if (!rect || !origin) return null
	return { top: rect.top - origin.top, left: rect.left - origin.left, width: rect.width, height: rect.height }
}
let frame = 0
function track() {
	hoverBox.value = boxOf(hovered.value)
	selectBox.value = boxOf(selected.value)
	// the agent removed the selected element
	if (selected.value && !selectBox.value && !editing.value) selected.value = null
	frame = requestAnimationFrame(track)
}
onMounted(() => (frame = requestAnimationFrame(track)))
onBeforeUnmount(() => {
	cancelAnimationFrame(frame)
	finishEdit(true)
})

const boxStyle = (box: Box, inset = 0) => ({
	top: `${box.top - inset}px`,
	left: `${box.left - inset}px`,
	width: `${box.width + inset * 2}px`,
	height: `${box.height + inset * 2}px`,
})

const toolbarStyle = computed(() => {
	const box = selectBox.value
	const room = host.value
	if (!box || !room) return {}
	const width = toolbar.value?.offsetWidth ?? 280
	const height = 36
	const gap = 8
	let top = box.top - height - gap
	if (top < gap) top = box.top + box.height + gap
	if (top + height > room.clientHeight - gap) top = Math.max(gap, box.top + gap)
	const left = Math.min(Math.max(box.left, gap), room.clientWidth - width - gap)
	return { top: `${top}px`, left: `${left}px` }
})

function onKeydown(event: KeyboardEvent) {
	if (event.key !== "Escape" || !selected.value || editing.value || event.defaultPrevented) return
	// an open drawer closes first
	if (document.querySelector("[data-editor-drawer]")) return
	selected.value = null
	event.preventDefault()
}
onMounted(() => window.addEventListener("keydown", onKeydown))
onBeforeUnmount(() => window.removeEventListener("keydown", onKeydown))
</script>
