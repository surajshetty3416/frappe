import type Block from "@ui/utils/block"
import type { BlockStyleMap } from "@ui/types"
import { screens } from "frappe-ui/tailwind/tokens"

// The styles every app gets so its pages work on a phone without spelling it out. A block's own
// styles win: base styles over the desktop defaults, tablet and mobile styles over the small ones.

export const SMALL_BREAKPOINTS = new Set(["tablet", "mobile"])

const isRow = (styles: BlockStyleMap) => styles.display === "flex" && (styles.flexDirection ?? "row") === "row" && styles.flexWrap !== "wrap"
const isColumn = (block: Block) => block.isContainer() && block.baseStyles.flexDirection === "column"

// main and side: a row of two column containers
const isSplit = (block: Block) => block.isContainer() && isRow(block.baseStyles) && block.children.length === 2 && block.children.every(isColumn)

// cards side by side, as a board's columns: a row repeater, or three or more containers
const isStrip = (block: Block) =>
	block.isContainer() &&
	isRow(block.baseStyles) &&
	(block.children.some((child) => child.componentName === "Repeater" && isRow({ display: "flex", ...child.baseStyles })) ||
		(block.children.length >= 3 && block.children.every((child) => child.isContainer())))

const parentOf = (block: Block, name: string) => {
	const parent = block.getParentBlock()
	return parent?.componentName === name ? parent : null
}

// the least a column takes: its fixed width, or the floor of its minmax; a fraction gives way
const PHONE_WIDTH = 320
const FIRST_COLUMN = 120
const trackFloor = (track: string) => {
	const fixed = /^(?:minmax\(\s*)?([\d.]+)(rem|px)/.exec(track.trim())
	if (!fixed) return 0
	return Number(fixed[1]) * (fixed[2] === "rem" ? 16 : 1)
}

// a table, as a list with a header, whose columns do not fit a phone; a list with columns per
// breakpoint lays itself out
const isWideTable = (list: Block) => {
	const columns = list.getProp("columns")
	if (!Array.isArray(columns) || !list.children.some((child) => child.componentName === "ListHeader")) return false
	// the first column is the row's name, which needs room to read
	const floors = columns.map((track: unknown, index: number) => Math.max(trackFloor(String(track)), index ? 0 : FIRST_COLUMN))
	return floors.reduce((sum: number, floor: number) => sum + floor + 8, 0) > PHONE_WIDTH
}

// a row that opens a record gets a hover surface and an inset; the header takes the same inset
const hasInteractiveRows = (list: Block) =>
	list.getChildrenAndSlotContent().some((child) =>
		child.getChildrenAndSlotContent().some((row) => row.componentName === "ListRow" && (row.getProp("route") || row.getProp("href") || row.componentEvents?.click))
	)

export function desktopDefaults(block: Block): BlockStyleMap {
	if (block.componentName === "List" && hasInteractiveRows(block)) return { "--list-row-padding-x": "0.75rem" } as BlockStyleMap
	return {}
}

// the edge a strip clips fades while there is more past it, by the keyframes in styles/scrollFade.css
const SCROLL_FADE = {
	maskImage: "linear-gradient(to right, transparent, #000 var(--scroll-fade-start), #000 calc(100% - var(--scroll-fade-end)), transparent)",
	animationName: "scroll-fade-x",
	animationDuration: "auto",
	animationTimingFunction: "linear",
	animationFillMode: "both",
	animationTimeline: "scroll(self inline)",
} as BlockStyleMap

// Below the tablet breakpoint main and side stack, a strip of cards scrolls inside itself, and a
// table too wide for a phone shows each row as its first cell over a muted line of the others.
export function smallDefaults(block: Block, breakpoint: string): BlockStyleMap {
	if (!SMALL_BREAKPOINTS.has(breakpoint)) return {}
	const parent = block.getParentBlock()
	const styles: BlockStyleMap = {}
	if (isSplit(block)) Object.assign(styles, { flexDirection: "column", alignItems: "stretch" })
	if (isStrip(block)) Object.assign(styles, { overflowX: "auto", ...SCROLL_FADE })
	if (block.isContainer() && parent?.isContainer() && isRow(parent.baseStyles) && parent.getRenderStyles(breakpoint).flexDirection === "column")
		Object.assign(styles, { width: "100%", maxWidth: "100%", flexShrink: 1 })

	const list = block.closest("List")
	if (!list || !isWideTable(list)) return styles
	if (block.componentName === "ListHeader" && parentOf(block, "List")) styles.display = "none"
	if (block.componentName === "ListRow")
		Object.assign(styles, { display: "flex", flexWrap: "wrap", alignItems: "center", height: "auto", columnGap: "12px", rowGap: "2px", paddingTop: "10px", paddingBottom: "10px" })
	const row = parentOf(block, "ListRow")
	if (block.componentName === "ListCell" && row && row.children.indexOf(block) === 0) styles.flexBasis = "100%"
	const cell = parentOf(block, "ListCell")
	const cellRow = cell && parentOf(cell, "ListRow")
	if (block.componentName === "TextBlock" && cellRow && cellRow.children.indexOf(cell) > 0) styles.color = "var(--ink-gray-5)"
	return styles
}

// A list's columns per screen, as the List's media rules pick them for a window this wide
export function columnsAt(columns: unknown, width: number) {
	if (!columns || typeof columns !== "object" || Array.isArray(columns)) return columns
	const tiers = columns as Record<string, string[] | undefined>
	const screen = Object.entries(screens)
		.filter(([name, min]) => tiers[name]?.length && parseFloat(min) <= width)
		.at(-1)
	return screen ? tiers[screen[0]] : tiers.base
}
