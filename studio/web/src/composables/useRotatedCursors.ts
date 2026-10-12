import type Block from "@web/block";
import resizeCursorSvg from "@web/assets/resize-cursor.svg?raw";
import rotationCursorSvg from "@web/assets/rotation-cursor.svg?raw";
import { getRotatedCursor } from "@web/utils/cursor";
import { getTotalRotation } from "@web/utils/rotation";
import { computed } from "vue";

// Cursors for the drag handles of a block, turned to match its *rendered* angle - its own
// rotation plus any rotated ancestors - so a handle always points along the edge it drags.
export function useRotatedCursors(getTarget: () => Element, getBlock: () => Block) {
	const rotation = computed(() => getTotalRotation(getTarget(), getBlock()));

	const resizeCursor = (offset: number, fallback: string) =>
		computed(() => getRotatedCursor(resizeCursorSvg, rotation.value + offset, fallback));

	return {
		rotation,
		horizontalCursor: resizeCursor(0, "ew-resize"),
		verticalCursor: resizeCursor(90, "ns-resize"),
		// top-left/bottom-right share one diagonal (nwse), top-right/bottom-left the other (nesw)
		cornerCursorNWSE: resizeCursor(45, "nwse-resize"),
		cornerCursorNESW: resizeCursor(-45, "nesw-resize"),
		rotationCursor: (baseAngle: number) =>
			computed(() => getRotatedCursor(rotationCursorSvg, rotation.value + baseAngle, "pointer")),
	};
}
