import useCanvasStore from "@ui/stores/canvasStore"
import blockController from "@ui/utils/blockController"
import { useKeyboardShortcut } from "frappe-ui"

const canvasStore = useCanvasStore()

export function useStudioEvents() {
	const shortcuts = [
		{
			combo: "Mod+Z",
			description: "Undo",
			group: "Edit",
			handler: () => {
				const history = canvasStore.activeCanvas?.history
				if (history?.canUndo()) history.undo()
			},
		},
		{
			combo: "Mod+Shift+Z",
			description: "Redo",
			group: "Edit",
			handler: () => {
				const history = canvasStore.activeCanvas?.history
				if (history?.canRedo()) history.redo()
			},
		},
		{
			combo: "Mod+D",
			description: "Duplicate Block",
			group: "Edit",
			handler: duplicateSelection,
		},
		...(["Backspace", "Delete"] as const).map((combo) => ({
			combo,
			description: "Delete Selected Blocks",
			group: "Edit",
			handler: deleteSelection,
		})),
	]
	// combos are plain strings here: Studio's frappe-ui import is untyped (src/lib.d.ts)
	useKeyboardShortcut(shortcuts as Parameters<typeof useKeyboardShortcut>[0])
}

export const duplicateSelection = () => {
	if (!blockController.isAnyBlockSelected() || blockController.multipleBlocksSelected()) return
	blockController.getSelectedBlocks()[0].duplicateBlock()
}

export const deleteSelection = (e?: KeyboardEvent) => {
	// a selected slot takes precedence over its (also-selected) parent block
	const selectedSlot = canvasStore.activeCanvas?.selectedSlot
	if (selectedSlot) {
		const parent = canvasStore.activeCanvas?.findBlock(selectedSlot.parentBlockId)
		parent?.removeSlot(selectedSlot.slotName)
		e?.stopPropagation()
		return
	}

	if (blockController.isAnyBlockSelected()) {
		for (const block of blockController.getSelectedBlocks()) {
			canvasStore.activeCanvas?.removeBlock(block)
		}
		blockController.clearSelection()
		if (document.activeElement instanceof HTMLElement) document.activeElement.blur()
		e?.stopPropagation()
	}
}
