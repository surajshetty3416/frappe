import { defineStore } from "pinia"
import { ref, reactive, nextTick } from "vue"
import type Block from "@ui/utils/block"

import type StudioCanvas from "@ui/components/StudioCanvas.vue"
import type { IndicatorGeometry } from "@ui/utils/dropGeometry"

const useCanvasStore = defineStore("studioCanvasStore", () => {
	const activeCanvas = ref<InstanceType<typeof StudioCanvas> | null>(null)
	const guides = reactive({
		showX: false,
		showY: false,
		x: 0,
		y: 0,
	})

	// dialogs
	const showHTMLDialog = ref(false)
	const editableBlock = ref<Block | null>(null)

	function editHTML(block: Block) {
		editableBlock.value = block
		nextTick(() => {
			showHTMLDialog.value = true
		})
	}

	function closeHTMLDialog() {
		showHTMLDialog.value = false
		editableBlock.value = null
	}

	const showCodeDialog = ref(false)
	const editableCode = ref({
		propName: "" as string,
		code: "" as string,
	})
	function editCode(block: Block, propName: string, code: string) {
		editableBlock.value = block
		editableCode.value.code = code
		editableCode.value.propName = propName
		nextTick(() => {
			showCodeDialog.value = true
		})
	}

	const isDragging = ref(false)

	// On-canvas block reordering (pointer-based). Separate from dropTarget
	// (panel → canvas drops). The overlay DropIndicator reads this; nothing here
	// touches the canvas DOM, so the layout stays frozen during a drag.
	const reorderTarget = reactive({
		active: <boolean>false,
		// insertion line geometry, screen px
		line: <IndicatorGeometry | null>null,
		containerRect: <{ top: number; left: number; width: number; height: number } | null>null,
		// dropping into a named slot (purple accent) vs regular children (blue)
		isSlotTarget: <boolean>false,
		// dropping into the block's own container (reorder) vs a different one
		isSameContainer: <boolean>false,
	})

	function clearReorderTarget() {
		Object.assign(reorderTarget, {
			active: false,
			line: null,
			containerRect: null,
			isSlotTarget: false,
			isSameContainer: false,
		})
	}

	// Ignore the click after a drag so the block selected at pickup stays selected
	const preventClick = ref(false)

	return {
		// layout
		activeCanvas,
		guides,
		// dialogs
		showHTMLDialog,
		editableBlock,
		editHTML,
		closeHTMLDialog,
		showCodeDialog,
		editCode,
		editableCode,
		isDragging,
		// on-canvas reorder
		reorderTarget,
		clearReorderTarget,
		preventClick,
	}
})

export default useCanvasStore