<template>
	<div data-layer="shell" class="pointer-events-none absolute inset-0 z-[1001]">
		<button
			v-for="pin in pins"
			:key="pin.key"
			type="button"
			data-selection-ui
			data-comment-ui
			class="pointer-events-auto absolute grid size-6 -translate-y-full place-items-center rounded-full rounded-bl-1 bg-surface-blue-6 text-xs font-medium text-ink-base border-2 border-[color:var(--surface-base)] shadow-md transition-transform hover:scale-110"
			:class="pin.open ? 'scale-110' : ''"
			:style="{ left: `${pin.left}px`, top: `${pin.top}px` }"
			:aria-label="`Comment ${pin.n}`"
			:title="pin.body"
			@click="openPin(pin.key)"
		>
			{{ pin.n }}
		</button>

		<div
			v-if="draft && popover"
			ref="card"
			data-selection-ui
			data-comment-ui
			class="pointer-events-auto absolute w-72 rounded-6 border border-outline-gray-2 bg-surface-base p-2 shadow-xl"
			:style="{ left: `${popover.left}px`, top: `${popover.top}px` }"
		>
			<div class="flex h-6 items-center gap-1.5 px-1 text-sm text-ink-gray-5">
				<span class="lucide-square-mouse-pointer size-4 shrink-0" />
				<span class="min-w-0 flex-1 truncate">{{ draft.element.label }}</span>
				<Button v-if="draft.key" size="sm" variant="ghost" icon="lucide-trash-2" tooltip="Delete comment" @click="remove" />
			</div>
			<div class="mt-1.5 flex items-center gap-1.5">
				<TextInput
					ref="input"
					v-model="body"
					class="flex-1"
					placeholder="Add a comment"
					@keydown.enter.prevent="closeDraft(true)"
					@keydown.esc.stop.prevent="closeDraft(false)"
				/>
				<Button
					variant="solid"
					icon="lucide-arrow-up"
					class="!rounded-full"
					:tooltip="draft.key ? 'Save' : 'Add to chat'"
					:disabled="!body.trim()"
					@click="closeDraft(true)"
				/>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { Button, TextInput } from "frappe-ui"
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue"

import { closeDraft, comments, draft, removeComment } from "../context"
import type { ArtifactEditor } from "../editor"

const props = defineProps<{ editor: ArtifactEditor; artifact: string; host: HTMLElement | null }>()

const input = ref<{ focus: () => void } | null>(null)
const card = ref<HTMLElement | null>(null)
// pin positions, in the host's coordinates, refreshed every frame
const spots = ref<Record<string, { left: number; top: number } | null>>({})

// the key of a pin not yet saved
const NEW = "new"
const pins = computed(() => {
	const list = comments.value.flatMap((comment, i) =>
		comment.artifact === props.artifact
			? [{ key: String(comment.key), n: i + 1, body: comment.body, open: draft.value?.key === comment.key }]
			: []
	)
	if (draft.value && !draft.value.key && draft.value.artifact === props.artifact)
		list.push({ key: NEW, n: comments.value.length + 1, body: "", open: true })
	return list.flatMap((pin) => {
		const spot = spots.value[pin.key]
		return spot ? [{ ...pin, ...spot }] : []
	})
})

function spotOf(element: string, x: number, y: number) {
	const rect = props.editor.elementRect(element)
	const origin = props.host?.getBoundingClientRect()
	if (!rect || !origin || !rect.width) return null
	const left = rect.left - origin.left + x * rect.width
	const top = rect.top - origin.top + y * rect.height
	// a pin past the preview's edge stays at the edge
	return { left: Math.min(Math.max(left, 4), origin.width - 28), top: Math.min(Math.max(top, 28), origin.height - 4) }
}

let frame = 0
function track() {
	const next: Record<string, { left: number; top: number } | null> = {}
	for (const comment of comments.value)
		if (comment.artifact === props.artifact) next[String(comment.key)] = spotOf(comment.element.id, comment.x, comment.y)
	const open = draft.value
	if (open && !open.key && open.artifact === props.artifact) next[NEW] = spotOf(open.element.id, open.x, open.y)
	spots.value = next
	frame = requestAnimationFrame(track)
}
onMounted(() => (frame = requestAnimationFrame(track)))
onBeforeUnmount(() => cancelAnimationFrame(frame))

const popover = computed(() => {
	const open = draft.value
	// a new pin's popover shows at once, before the next frame places the pin
	const spot = open && (spots.value[open.key ? String(open.key) : NEW] ?? spotOf(open.element.id, open.x, open.y))
	const room = props.host
	if (!spot || !room) return null
	const width = 288
	const height = card.value?.offsetHeight ?? 84
	const gap = 8
	let left = spot.left + 28 + gap
	if (left + width > room.clientWidth - gap) left = spot.left - width - gap
	left = Math.max(gap, left)
	const top = Math.min(Math.max(spot.top - 24, gap), room.clientHeight - height - gap)
	return { left, top }
})

// the input can still emit as its popover closes
const body = computed({
	get: () => draft.value?.body ?? "",
	set: (value: string) => draft.value && (draft.value.body = value),
})

// the popover shows a frame after its pin, and takes the keyboard as it does
watch(input, (shown) => shown?.focus())

function openPin(key: string) {
	if (key === NEW) return
	closeDraft(true)
	const comment = comments.value.find((comment) => String(comment.key) === key)
	if (comment) draft.value = { ...comment }
}

function remove() {
	const key = draft.value?.key
	draft.value = null
	if (key) removeComment(key)
}

// a press outside the popover keeps what was typed
function onPointerDown(event: PointerEvent) {
	if (!draft.value || (event.target instanceof Element && event.target.closest("[data-comment-ui]"))) return
	closeDraft(true)
}
onMounted(() => window.addEventListener("pointerdown", onPointerDown, true))
onBeforeUnmount(() => window.removeEventListener("pointerdown", onPointerDown, true))
</script>
