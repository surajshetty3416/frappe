<!-- The list that floats above the composer: the skills a "/" offers. -->
<template>
	<div class="fixed inset-0 z-10" @click="emit('close')" />
	<section
		ref="panel"
		tabindex="-1"
		:aria-label="title"
		class="flow-palette-panel absolute bottom-[calc(100%+8px)] left-0 z-20 flex max-h-[min(400px,60vh)] w-full flex-col overflow-hidden rounded-6 border border-outline-gray-2 bg-surface-white shadow-xl outline-none"
		@pointerover="onPointerOver"
	>
		<header class="flex h-9 flex-none items-center px-3 text-sm font-medium text-ink-gray-5">{{ title }}</header>
		<slot />
	</section>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref } from "vue"

import { nextNavigationIndex } from "../paletteNav.js"

const props = defineProps({
	title: { type: String, required: true },
	autofocus: { type: Boolean, default: true },
})
const emit = defineEmits(["close"])
const panel = ref(null)
let activeItem = null
let observer = null

function items() {
	return [...(panel.value?.querySelectorAll("[data-palette-item]:not(:disabled)") ?? [])]
}

function setActive(item) {
	activeItem?.removeAttribute("data-palette-active")
	activeItem = item
	activeItem?.setAttribute("data-palette-active", "true")
}

function syncItems() {
	const rows = items()
	if (!rows.includes(activeItem)) {
		setActive(rows.find((row) => row.getAttribute("aria-current") === "true") ?? rows[0] ?? null)
	}
}

function onPointerOver(event) {
	const item = event.target.closest?.("[data-palette-item]:not(:disabled)")
	if (item && panel.value?.contains(item)) setActive(item)
}

// Capture at window level so palettes work whether focus lives in their search
// input, their panel, or the composer textarea behind the slash-command list.
function onKey(event) {
	if (event.key === "Escape") {
		event.preventDefault()
		event.stopPropagation()
		emit("close")
		return
	}
	const rows = items()
	const current = rows.indexOf(activeItem)
	const nextIndex = nextNavigationIndex(current, rows.length, event.key)
	if (nextIndex !== null) {
		event.preventDefault()
		event.stopPropagation()
		setActive(rows[nextIndex])
		activeItem.scrollIntoView({ block: "nearest" })
	} else if (event.key === "Enter" && activeItem) {
		event.preventDefault()
		event.stopPropagation()
		activeItem.click()
	}
}

onMounted(async () => {
	window.addEventListener("keydown", onKey, true)
	observer = new MutationObserver(syncItems)
	observer.observe(panel.value, { childList: true, subtree: true })
	await nextTick()
	syncItems()
	// Search palettes focus their input first; list-only palettes focus the panel.
	if (props.autofocus && !panel.value?.contains(document.activeElement)) {
		panel.value?.focus({ preventScroll: true })
	}
})
onBeforeUnmount(() => {
	window.removeEventListener("keydown", onKey, true)
	observer?.disconnect()
})
</script>

<style scoped>
.flow-palette-panel :deep([data-palette-item][data-palette-active="true"]) {
	background: var(--surface-gray-2);
}
</style>
