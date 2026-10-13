<template>
	<div
		ref="host"
		class="relative isolate h-full overflow-hidden"
		:data-commenting="commenting && editor ? '' : undefined"
		@mouseover.capture="onPointer"
		@mousemove.capture="onPointer"
		@mousedown.capture="onMouseDown"
		@click.capture="onClick"
		@dblclick.capture="onDoubleClick"
		@contextmenu.capture="onContextMenu"
		@mouseleave="hovered = null"
	>
		<slot />
		<div v-if="shellEditor" data-layer="shell" class="pointer-events-none absolute inset-0 z-[1000]">
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
			<div
				v-if="resizeBox"
				class="absolute rounded-[2px] border border-dashed border-outline-blue-5"
				:style="boxStyle(resizeBox)"
			/>
			<span
				v-if="selectBox && canResize && !editing && !commenting"
				data-selection-ui
				class="pointer-events-auto absolute size-3 cursor-se-resize rounded-[2px] border-2 border-outline-blue-5 bg-surface-base"
				:style="{ top: `${(resizeBox ?? selectBox).top + (resizeBox ?? selectBox).height - 5}px`, left: `${(resizeBox ?? selectBox).left + (resizeBox ?? selectBox).width - 5}px` }"
				@pointerdown.stop.prevent="startResize"
			/>
		</div>
		<PreviewComments v-if="shellEditor" :editor="editor!" :artifact="artifact" :host="host" />
		<div
			v-if="shellEditor && commenting"
			data-selection-ui
			data-layer="shell"
			class="absolute left-1/2 top-3 z-[1002] flex h-9 -translate-x-1/2 items-center gap-2 rounded-full border border-outline-gray-2 bg-surface-base pl-3 pr-1 shadow-lg"
		>
			<span class="lucide-message-square-plus size-4 text-ink-gray-5" />
			<span class="whitespace-nowrap text-sm text-ink-gray-7">Click an element to comment on it</span>
			<Button size="sm" variant="subtle" label="Done" class="!rounded-full" @click="commenting = false" />
		</div>
		<div
			v-if="shellEditor && selected && selectBox && !editing && !commenting && !covered && !resizeBox"
			ref="toolbar"
			data-selection-ui
			data-layer="shell"
			class="absolute z-[1002] flex h-9 items-center gap-0.5 rounded-6 border border-outline-gray-2 bg-surface-base p-1 shadow-lg"
			:style="toolbarStyle"
		>
			<span class="flex max-w-[160px] items-center gap-1.5 px-1.5 text-sm text-ink-gray-6">
				<span :class="selected.icon" class="size-4 shrink-0 text-ink-gray-5" />
				<span class="truncate">{{ selected.label }}</span>
			</span>
			<div class="mx-0.5 h-4 w-px bg-surface-gray-3" />
			<Button variant="ghost" icon="lucide-message-square-plus" tooltip="Comment" @click="commentOnSelected" />
			<Button v-if="selected.hasText" variant="ghost" icon="lucide-type" tooltip="Edit text" @click="startEdit" />
			<Button
				v-for="action in actions"
				:key="action.name"
				variant="ghost"
				:icon="action.icon"
				:tooltip="ACTION_KEYS[action.name] ? `${action.label} (${ACTION_KEYS[action.name]})` : action.label"
				:aria-label="action.label"
				@click="runAction(action)"
			/>
			<template v-if="properties.length">
				<div class="mx-0.5 h-4 w-px bg-surface-gray-3" />
				<PropertyControl v-for="property in properties" :key="property.name" :property="property" />
			</template>
		</div>
	</div>
</template>

<script setup lang="ts">
import { Button, toast } from "frappe-ui"
import { computed, nextTick, onBeforeUnmount, onMounted, ref, shallowRef, watch } from "vue"

import { closeDraft, commenting, describeElement, draft, selection } from "../context"
import { type ArtifactEditor, type ElementAction, type PreviewElement, editorMode } from "../editor"
import PreviewComments from "./PreviewComments.vue"
import PropertyControl from "./PropertyControl.vue"

// `covered`: a drawer lies over the preview
const props = defineProps<{ editor: ArtifactEditor | null; artifact: string; covered?: boolean }>()

type Box = { top: number; left: number; width: number; height: number }

const host = ref<HTMLElement | null>(null)
const toolbar = ref<HTMLElement | null>(null)
const hovered = shallowRef<PreviewElement | null>(null)
const selected = shallowRef<PreviewElement | null>(null)
const hoverBox = ref<Box | null>(null)
const selectBox = ref<Box | null>(null)
const editing = ref<{ id: string; node: HTMLElement; original: string } | null>(null)
// the editor while in Edit: the shell draws and takes the pointer only then; in Preview clicks reach the preview
const shellEditor = computed(() => (props.editor && editorMode.value === "edit" ? props.editor : null))
watch(shellEditor, (on) => {
	if (on) return
	finishEdit(true)
	hovered.value = selected.value = null
})

watch(
	() => [props.editor, props.artifact],
	() => {
		finishEdit(false)
		closeDraft(true)
		hovered.value = selected.value = null
	}
)

// the chat tells the agent what is selected, and the layer hears it too
watch(selected, (element, before) => {
	describeSelection()
	if (element?.id !== before?.id) props.editor?.select?.(element?.id ?? null)
})
function describeSelection() {
	selection.value = selected.value && props.editor ? describeElement(props.editor, selected.value) : null
}
onBeforeUnmount(() => (selection.value = null))

watch(commenting, (on) => {
	if (on) selected.value = null
	else closeDraft(true)
})

function commentOn(element: PreviewElement, x: number, y: number) {
	if (!props.editor) return
	closeDraft(true)
	draft.value = { artifact: props.artifact, element: describeElement(props.editor, element), x, y, body: "" }
}
function commentOnSelected() {
	const element = selected.value
	if (!element) return
	selected.value = null
	commentOn(element, 0, 0)
}

const properties = computed(() => (selected.value && props.editor ? props.editor.properties(selected.value.id).slice(0, 4) : []))
const actions = computed(() => (selected.value && props.editor?.actions ? props.editor.actions(selected.value.id) : []))
const ACTION_KEYS: Record<string, string> = { delete: "Delete", duplicate: "⌘D" }
async function runAction(action: ElementAction) {
	try {
		await action.run()
	} catch (error) {
		toast.error((error as Error)?.message || "That did not work")
	}
}

const canResize = computed(() => Boolean(selected.value && props.editor?.resize && props.editor.resizable?.(selected.value.id)))
const resizeBox = ref<Box | null>(null)
function startResize(event: PointerEvent) {
	const element = selected.value
	const from = selectBox.value
	if (!element || !from) return
	const { clientX, clientY } = event
	const move = (moved: PointerEvent) => {
		resizeBox.value = {
			...from,
			width: Math.max(16, from.width + moved.clientX - clientX),
			height: Math.max(16, from.height + moved.clientY - clientY),
		}
	}
	const stop = () => {
		window.removeEventListener("pointermove", move)
		window.removeEventListener("pointerup", stop)
		const size = resizeBox.value
		resizeBox.value = null
		if (size) props.editor?.resize?.(element.id, { width: Math.round(size.width), height: Math.round(size.height) })
	}
	window.addEventListener("pointermove", move)
	window.addEventListener("pointerup", stop)
}

const ownsEvent = (event: Event) => {
	const target = event.target
	if (!shellEditor.value || !(target instanceof Element)) return false
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
	const found = elementAt(event)
	if (!commenting.value) {
		selected.value = found
		return
	}
	const rect = found && props.editor?.elementRect(found.id)
	if (found && rect) commentOn(found, (event.clientX - rect.left) / rect.width, (event.clientY - rect.top) / rect.height)
}
function onDoubleClick(event: MouseEvent) {
	if (!ownsEvent(event)) return
	event.stopPropagation()
	event.preventDefault()
	if (commenting.value) return
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
	if (save && node.innerHTML !== original) {
		props.editor?.setText(id, node.innerHTML)
		describeSelection()
		// the toolbar's label may be the text just edited
		nextTick(() => {
			const fresh = props.editor?.elementAt(props.editor.textNode(id) ?? node)
			if (fresh?.id === id && selected.value?.id === id) selected.value = fresh
		})
	} else if (!save) node.innerHTML = original
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
	// the preview insets its sheet; the toolbar stays inside it
	const inset = 24
	let top = box.top - height - gap
	if (top < gap) top = box.top + box.height + gap
	if (top + height > room.clientHeight - gap) top = Math.max(gap, box.top + gap)
	const centered = box.left + box.width / 2 - width / 2
	const left = Math.min(Math.max(centered, inset), room.clientWidth - width - inset)
	return { top: `${top}px`, left: `${left}px` }
})

function onKeydown(event: KeyboardEvent) {
	if (event.key === "Escape" && commenting.value && !event.defaultPrevented) {
		commenting.value = false
		event.preventDefault()
		return
	}
	const element = selected.value
	const typing = event.target instanceof HTMLElement && event.target.closest('input, textarea, select, [contenteditable="true"], .cm-editor')
	if (element && !editing.value && !typing && !event.defaultPrevented && shellEditor.value) {
		const name =
			event.key === "Delete" || event.key === "Backspace"
				? "delete"
				: event.key.toLowerCase() === "d" && (event.metaKey || event.ctrlKey)
					? "duplicate"
					: null
		const action = name && actions.value.find((action) => action.name === name)
		if (action) {
			event.preventDefault()
			runAction(action)
			return
		}
	}
	if (event.key !== "Escape" || !selected.value || editing.value || event.defaultPrevented) return
	// an open drawer closes first
	if (document.querySelector("[data-editor-drawer]")) return
	selected.value = null
	event.preventDefault()
}
onMounted(() => window.addEventListener("keydown", onKeydown))
onBeforeUnmount(() => window.removeEventListener("keydown", onKeydown))
</script>
