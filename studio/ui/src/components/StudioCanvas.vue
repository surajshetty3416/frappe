<template>
	<div ref="canvasContainer" @click="handleClick">
		<div class="overlay absolute" ref="overlay" />
		<DropIndicator />
		<BlockSnapGuides />
		<Transition name="fade">
			<div
				class="absolute bottom-0 left-0 right-0 top-0 z-[19] grid w-full place-items-center bg-surface-gray-1"
				v-show="store.settingPage"
			>
				<LoadingIndicator class="h-5 w-5 text-ink-gray-6" />
			</div>
		</Transition>

		<div
			class="fixed flex flex-col"
			ref="canvas"
			:style="{
				transformOrigin: 'top center',
				transform: `scale(${canvasProps.scale}) translate(${canvasProps.translateX}px, ${canvasProps.translateY}px)`,
			}"
		>
			<div class="flex">
				<div
					class="canvas relative flex min-h-[100dvh] bg-surface-base shadow-2xl contain-layout"
					v-for="breakpoint in visibleBreakpoints"
					:key="breakpoint.device"
					:style="{
						...canvasStyles,
						background: canvasProps.background,
						width: `${breakpoint.width}px`,
					}"
				>
					<StudioComponent
						class="h-full min-h-[inherit]"
						v-if="showBlocks && rootComponent"
						:block="rootComponent"
						:key="rootComponent.componentId"
						:breakpoint="breakpoint.device"
					/>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { Ref, ref, watch, reactive, computed, onMounted, provide } from "vue"
import { LoadingIndicator } from "frappe-ui"
import StudioComponent from "@ui/components/StudioComponent.vue"
import DropIndicator from "@ui/components/DropIndicator.vue"
import BlockSnapGuides from "@ui/components/BlockSnapGuides.vue"

import useStudioStore from "@ui/stores/studioStore"
import useCanvasStore from "@ui/stores/canvasStore"
import { getBlockInfo } from "@ui/utils/helpers"
import setPanAndZoom from "@ui/utils/panAndZoom"
import Block from "@ui/utils/block"
import { useCanvasUtils } from "@ui/utils/useCanvasUtils"
import type { BreakpointConfig, CanvasHistory } from "@ui/types/StudioCanvas"
import type { Slot } from "@ui/types"
import { getBlockCopy } from "@ui/utils/serializer"
import { useCanvasNavigationGuard } from "@ui/utils/useCanvasNavigationGuard"

const props = defineProps({
	componentTree: {
		type: Block,
		required: true,
	},
	canvasStyles: {
		type: Object,
		default: () => ({}),
	},
})
const store = useStudioStore()
const canvasStore = useCanvasStore()

const canvasContainer = ref(null)
const canvas = ref<HTMLElement | null>(null)
const overlay = ref(null)
const showBlocks = ref(false)

const canvasProps = reactive({
	overlayElement: null,
	background: "#fff",
	scale: 1,
	translateX: 0,
	translateY: 0,
	settingCanvas: true,
	scaling: false,
	panning: false,
	breakpoints: [
		{
			icon: "lucide-monitor",
			device: "desktop",
			displayName: "Desktop",
			width: 1400,
			visible: true,
		},
		{
			icon: "lucide-tablet",
			device: "tablet",
			displayName: "Tablet",
			width: 800,
			visible: false,
		},
		{
			icon: "lucide-smartphone",
			device: "mobile",
			displayName: "Mobile",
			width: 420,
			visible: false,
		},
	] as BreakpointConfig[],
})
provide("canvasProps", canvasProps)

const visibleBreakpoints = computed(() => {
	return canvasProps.breakpoints.filter((breakpoint) => breakpoint.visible)
})

watch(
	() => canvasProps.breakpoints.map((b) => b.visible),
	() => {
		if (canvasProps.settingCanvas) {
			return
		}
		setScaleAndTranslate()
	},
)
function setBreakpoint(device: BreakpointConfig["device"]) {
	canvasProps.breakpoints.forEach((breakpoint) => (breakpoint.visible = breakpoint.device === device))
	setActiveBreakpoint(device)
}

// clone props.block into canvas data to avoid mutating them
const rootComponent = ref(getBlockCopy(props.componentTree, true))
const history = ref(null) as Ref<null> | CanvasHistory

// block hover & selection
const hoveredBlock = ref<string | null>(null)
const hoveredBreakpoint = ref<string | null>("desktop")
const activeBreakpoint = ref<string | null>("desktop")

function setHoveredBlock(blockId: string | null) {
	hoveredBlock.value = blockId
}
function setHoveredBreakpoint(breakpoint: string | null) {
	hoveredBreakpoint.value = breakpoint
}
function setActiveBreakpoint(breakpoint: string | null) {
	activeBreakpoint.value = breakpoint
}

const selectedBlockIds = ref<Set<string>>(new Set())
// anchor for shift-click range selection, set by plain/multi clicks and held fixed across shift-clicks
const selectionAnchorId = ref<string | null>(null)
const selectedBlocks = computed(() => {
	return (
		Array.from(selectedBlockIds.value)
			.map((id) => findBlock(id))
			// filter out missing blocks/null values
			.filter((b) => b)
	)
}) as Ref<Block[]>

function selectBlock(block: Block, e: MouseEvent | null, setBreakpoint = true) {
	if (store.settingPage) return

	if (e && e.shiftKey) {
		selectBlockRange(block)
	} else if (e && (e.metaKey || e.ctrlKey)) {
		toggleBlockSelection(block)
	} else {
		selectBlockById(block.componentId)
		// family-specific selection behavior (e.g. selecting a nav item activates its tab)
		Block.getComponents()?.[block.componentName]?.onSelect?.(block)
	}

	if (setBreakpoint && e) {
		const { breakpoint } = getBlockInfo(e)
		setActiveBreakpoint(breakpoint)
	}
}

function selectBlockById(blockId: string) {
	selectedBlockIds.value = new Set([blockId])
	selectionAnchorId.value = blockId
}

function toggleBlockSelection(block: Block) {
	if (selectedBlockIds.value.has(block.componentId)) {
		selectedBlockIds.value.delete(block.componentId)
	} else {
		selectedBlockIds.value.add(block.componentId)
	}
	selectionAnchorId.value = block.componentId
}

function selectBlockRange(block: Block) {
	const anchor = selectionAnchorId.value ? findBlock(selectionAnchorId.value) : null
	const parent = anchor?.getParentBlock()
	// range selection only works among siblings sharing a parent AND slot; otherwise fall back to single select
	if (
		!anchor ||
		!parent ||
		parent !== block.getParentBlock() ||
		anchor.parentSlotName !== block.parentSlotName
	) {
		selectBlockById(block.componentId)
		return
	}
	const siblings = anchor.parentSlotName
		? (parent.getSlotContent(anchor.parentSlotName) as Block[])
		: parent.children
	// replace the selection with the anchor→block range so repeated shift-clicks grow/shrink it
	const start = parent.getChildIndex(anchor)
	const end = parent.getChildIndex(block)
	const range = siblings.slice(Math.min(start, end), Math.max(start, end) + 1)
	selectedBlockIds.value = new Set(range.map((child) => child.componentId))
}

const handleClick = (ev: MouseEvent) => {
	if (canvasStore.preventClick) return
	const target = document.elementFromPoint(ev.clientX, ev.clientY)
	// hack to ensure if click is on canvas-container
	// TODO: Still clears selection if space handlers are dragged over canvas-container
	if (target?.classList.contains("canvas-container")) {
		clearSelection()
	}
}

function clearSelection() {
	selectedBlockIds.value = new Set()
	selectionAnchorId.value = null
}

const isRootSelected = computed(() => {
	return (
		selectedBlockIds.value.size === 1 && selectedBlockIds.value.has(rootComponent.value?.componentId || "")
	)
})

// slots
const selectedSlot = ref<Slot | null>()
function selectSlot(slot: Slot) {
	selectedSlot.value = slot
	selectBlockById(slot.parentBlockId)
}

const activeSlotIds = computed(() => {
	const slotIds = new Set<string>()
	for (const block of selectedBlocks.value) {
		for (const slot of Object.values(block.componentSlots)) {
			slotIds.add(slot.slotId)
		}
	}
	return slotIds
})

const {
	setScaleAndTranslate,
	setupHistory,
	getRootBlock,
	setRootBlock,
	findBlock,
	removeBlock,
	scrollBlockIntoView,
} = useCanvasUtils(canvasProps, canvasContainer, canvas, rootComponent, selectedBlockIds, history)

watch(
	() => activeSlotIds.value,
	(map) => {
		// clear selected slot if the block is deleted, not selected anymore, or the slot is removed from the block
		if (selectedSlot.value && !map.has(selectedSlot.value.slotId)) {
			selectedSlot.value = null
		}
	},
	{ immediate: true },
)

useCanvasNavigationGuard(canvasContainer)

onMounted(() => {
	const canvasContainerEl = canvasContainer.value as unknown as HTMLElement
	const canvasEl = canvas.value as unknown as HTMLElement
	canvasProps.overlayElement = overlay.value
	setScaleAndTranslate()
	showBlocks.value = true
	setupHistory()
	setPanAndZoom(canvasEl, canvasContainerEl, canvasProps)
})

defineExpose({
	history,
	rootComponent,
	canvasProps,
	canvasContainer,
	setBreakpoint,
	// canvas utils
	findBlock,
	removeBlock,
	getRootBlock,
	setRootBlock,
	// block hover & selection
	hoveredBlock,
	hoveredBreakpoint,
	activeBreakpoint,
	setHoveredBlock,
	setHoveredBreakpoint,
	setActiveBreakpoint,
	selectedBlockIds,
	selectedBlocks,
	selectBlock,
	scrollBlockIntoView,
	selectBlockById,
	toggleBlockSelection,
	selectBlockRange,
	clearSelection,
	isRootSelected,
	// slots
	selectedSlot,
	selectSlot,
	activeSlotIds,
})
</script>

<style>
.hovered-block {
	@apply border-outline-blue-3 text-ink-gray-6 dark:border-outline-blue-9 dark:text-ink-gray-4;
}
.block-selected {
	@apply border-outline-blue-4 text-ink-gray-8 dark:border-outline-blue-7 dark:text-ink-gray-1;
}
.slot-selected {
	@apply border-outline-purple-4 text-ink-gray-8;
}
#placeholder {
	@apply transition-all;
}
.vertical-placeholder {
	@apply mx-4 h-full min-h-5 w-auto border-l-2 border-dashed border-outline-blue-5;
}
.horizontal-placeholder {
	@apply my-4 h-auto w-full border-t-2 border-dashed border-outline-blue-5;
}
</style>
