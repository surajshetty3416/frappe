<template>
	<div class="flex flex-col">
		<!-- one height in every state, so the preview never moves -->
		<div v-if="editor" data-context-row data-layer="shell" class="flex h-9 shrink-0 items-center gap-1 border-b border-outline-gray-1 pl-3 pr-2">
			<template v-if="shellEditor && commenting">
				<span class="flex min-w-0 flex-1 items-center gap-2 text-sm text-ink-gray-7">
					<span class="lucide-message-square-plus size-4 shrink-0 text-ink-gray-5" />
					<span class="truncate">Click an element to comment on it</span>
				</span>
				<Button size="sm" variant="subtle" label="Done" @click="commenting = false" />
			</template>
			<template v-else-if="shellEditor && selected">
				<div class="flex min-w-0 flex-1 items-center gap-0.5">
					<span class="flex max-w-[160px] shrink-0 items-center gap-1.5 pr-1 text-sm font-medium text-ink-gray-8">
						<span :class="selected.icon" class="size-4 shrink-0 text-ink-gray-5" />
						<span class="truncate">{{ selected.label }}</span>
					</span>
					<template v-if="properties.length && !editing">
						<div class="mx-0.5 h-4 w-px shrink-0 bg-surface-gray-3" />
						<div
							ref="propertyRow"
							class="flex min-w-0 items-center gap-0.5 overflow-x-auto [scrollbar-width:none] [&>*]:shrink-0"
							:class="propertiesOverflow ? '[mask-image:linear-gradient(to_right,black_calc(100%-32px),transparent)]' : ''"
						>
							<PropertyControl v-for="property in properties" :key="property.name" :property="property" />
						</div>
					</template>
				</div>
				<span v-if="editing" class="shrink-0 whitespace-nowrap text-sm text-ink-gray-5">Enter to save, Esc to cancel</span>
				<div v-else class="flex shrink-0 items-center gap-0.5">
					<Button v-if="selected.hasText" variant="ghost" icon="lucide-type" tooltip="Edit text" aria-label="Edit text" @click="startEdit" />
					<Button variant="ghost" icon="lucide-message-square-plus" tooltip="Comment" aria-label="Comment" @click="commentOnSelected" />
					<Button
						v-for="action in actions"
						:key="action.name"
						variant="ghost"
						:icon="action.icon"
						:tooltip="ACTION_KEYS[action.name] ? `${action.label} (${ACTION_KEYS[action.name]})` : action.label"
						:aria-label="action.label"
						@click="runAction(action)"
					/>
					<Button variant="ghost" icon="lucide-x" tooltip="Clear selection (Esc)" aria-label="Clear selection" @click="selected = null" />
				</div>
			</template>
			<slot v-else name="idle" />
		</div>
		<div class="relative min-h-0 flex-1">
			<div
				ref="host"
				class="relative isolate h-full overflow-hidden"
				:data-layer="layer"
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
						class="absolute rounded-[2px] border border-outline-gray-3"
						:style="boxStyle(hoverBox, OUTLINE_OFFSET)"
					/>
					<div
						v-if="selectBox"
						class="absolute rounded-[2px] border-2 border-outline-blue-5"
						:style="boxStyle(selectBox, OUTLINE_OFFSET + 1)"
					/>
					<div
						v-if="resizeBox"
						class="absolute rounded-[2px] border border-dashed border-outline-blue-5"
						:style="boxStyle(resizeBox, OUTLINE_OFFSET)"
					/>
					<span
						v-if="selectBox && canResize && !editing && !commenting"
						data-selection-ui
						class="pointer-events-auto absolute size-3 cursor-se-resize rounded-[2px] border-2 border-outline-blue-5 bg-surface-base"
						:style="{ top: `${(resizeBox ?? selectBox).top + (resizeBox ?? selectBox).height + OUTLINE_OFFSET - 5}px`, left: `${(resizeBox ?? selectBox).left + (resizeBox ?? selectBox).width + OUTLINE_OFFSET - 5}px` }"
						@pointerdown.stop.prevent="startResize"
					/>
				</div>
				<PreviewComments v-if="shellEditor" :editor="editor!" :artifact="artifact" :host="host" />
			</div>
			<slot name="over" />
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

// `covered`: a drawer lies over the preview. `layer`: whose styles reach the preview
const props = defineProps<{ editor: ArtifactEditor | null; artifact: string; covered?: boolean; layer?: string }>()

type Box = { top: number; left: number; width: number; height: number }

const host = ref<HTMLElement | null>(null)
const propertyRow = ref<HTMLElement | null>(null)
// properties wider than the row scroll sideways, and fade at the edge to say so
const propertiesOverflow = ref(false)
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

// a drawer over the preview lets go of the selection, which would show through
watch(
	() => props.covered,
	(covered) => covered && (selected.value = null)
)

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
	const from = selected.value
	try {
		const made = await action.run()
		if (typeof made === "string" && from) selectMade(made, from)
	} catch (error) {
		toast.error((error as Error)?.message || "That did not work")
	}
}

// an action's new element (a duplicate) takes the selection once it is on screen
function selectMade(id: string, from: PreviewElement, frames = 30) {
	const rect = props.editor?.elementRect(id)
	if (!rect) {
		if (frames) requestAnimationFrame(() => selectMade(id, from, frames - 1))
		return
	}
	const atCentre = document
		.elementsFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2)
		.map((node) => props.editor?.elementAt(node))
		.find((element) => element?.id === id)
	selected.value = atCentre ?? { ...from, id }
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
	const row = propertyRow.value
	propertiesOverflow.value = Boolean(row && row.scrollWidth > row.clientWidth + 1 && row.scrollLeft + row.clientWidth < row.scrollWidth - 1)
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

const OUTLINE_OFFSET = 4

function onKeydown(event: KeyboardEvent) {
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
}
// Esc reaches the selection before the focused composer, which would stop the agent's turn with it.
// A drawer, popover, dialog, draft comment or text edit open on top takes Esc first.
function onEscape(event: KeyboardEvent) {
	if (event.key !== "Escape" || event.defaultPrevented || editing.value || draft.value) return
	if (!commenting.value && !selected.value) return
	if (document.querySelector("[data-editor-drawer], [data-reka-popper-content-wrapper]:not(:has([role=tooltip])), [role=dialog]")) return
	if (commenting.value) commenting.value = false
	else selected.value = null
	event.preventDefault()
	event.stopPropagation()
}
onMounted(() => {
	window.addEventListener("keydown", onKeydown)
	window.addEventListener("keydown", onEscape, true)
})
onBeforeUnmount(() => {
	window.removeEventListener("keydown", onKeydown)
	window.removeEventListener("keydown", onEscape, true)
})
</script>
