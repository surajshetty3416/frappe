<template>
	<!-- the shell draws the selection, so the canvas's own overlay stays hidden -->
	<div ref="room" data-app-preview class="relative h-full w-full overflow-hidden bg-surface-gray-2 [&_.overlay]:hidden" style="contain: paint">
		<StudioCanvas
			v-if="store.pageBlocks[0]"
			ref="pageCanvas"
			class="canvas-container absolute inset-0 flex justify-center overflow-hidden transition-opacity duration-150"
			:class="fitted && !store.settingPage ? 'opacity-100' : 'opacity-0'"
			:componentTree="store.pageBlocks[0]"
			:canvasStyles="frameStyles"
		/>
		<div v-if="!fitted || store.settingPage" class="absolute inset-0 grid place-items-center">
			<LoadingIndicator class="size-5 text-ink-gray-4" />
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch, watchEffect } from "vue"
import { useDebounceFn, useEventListener, useResizeObserver } from "@vueuse/core"
import { LoadingIndicator, toast } from "frappe-ui"

import StudioCanvas from "@ui/components/StudioCanvas.vue"
import useStudioStore from "@ui/stores/studioStore"
import useCanvasStore from "@ui/stores/canvasStore"

// One app page rendered with its data, editable by selection. The shell mounts this as the preview.
const props = defineProps<{ appID: string; pageID: string }>()

const store = useStudioStore()
const canvasStore = useCanvasStore()

const PAD = 24
const PHONE = { width: 390, height: 844, bezel: 10 }
const TABLET_WIDTH = 768
const TABLET_INSET = 20
// desktop lays out at its own width and zooms to fit the panel, so a narrow panel never reflows the page
const DESKTOP_WIDTH = 1280

const room = ref<HTMLElement | null>(null)
const pageCanvas = ref<InstanceType<typeof StudioCanvas> | null>(null)
const fitted = ref(false)
const minHeight = ref(0)
const zoom = ref(1)
watchEffect(() => (canvasStore.activeCanvas = pageCanvas.value))

const device = computed(
	() => pageCanvas.value?.canvasProps.breakpoints.find((breakpoint) => breakpoint.visible)?.device ?? "desktop",
)

const bezel = `0 0 0 ${PHONE.bezel}px var(--surface-gray-9), 0 24px 48px -12px rgb(0 0 0 / 0.3)`
const frameStyles = computed(() => {
	if (device.value === "mobile")
		return {
			height: `${PHONE.height}px`,
			minHeight: `${PHONE.height}px`,
			overflowY: "auto",
			borderRadius: "44px",
			// the status bar and home indicator keep the page off the rounded corners
			padding: "44px 0 20px",
			boxShadow: bezel,
		}
	// a tablet narrower than its own width still reads as one by its frame
	if (device.value === "tablet") return { minHeight: `${minHeight.value}px`, borderRadius: "20px", padding: `${TABLET_INSET}px 0`, boxShadow: bezel }
	// CSS zoom, not a transform, so the page's rects stay true for selection
	return { minHeight: `${minHeight.value / zoom.value}px`, zoom: zoom.value, boxShadow: `0 0 0 ${1 / zoom.value}px var(--outline-gray-2)` }
})

// desktop renders at 1280px or the panel's width and zooms to the panel, tablet at its own width or
// narrower; the phone frame scales down to fit
async function fit() {
	const el = room.value
	const canvas = pageCanvas.value
	if (!el || !canvas) return
	const canvasProps = canvas.canvasProps
	const width = el.clientWidth - PAD * 2
	const height = el.clientHeight - PAD * 2
	const breakpoint = canvasProps.breakpoints.find((breakpoint) => breakpoint.visible)
	if (!breakpoint || width <= 0) return

	let scale = 1
	if (breakpoint.device === "desktop") {
		breakpoint.width = Math.max(DESKTOP_WIDTH, width)
		zoom.value = width / breakpoint.width
		minHeight.value = height
	} else if (breakpoint.device === "tablet") {
		breakpoint.width = Math.min(TABLET_WIDTH, width - PHONE.bezel * 2)
		minHeight.value = height - PHONE.bezel * 2 - TABLET_INSET * 2
	} else {
		breakpoint.width = PHONE.width
		const frame = PHONE.bezel * 2
		scale = Math.min(1, width / (PHONE.width + frame), height / (PHONE.height + frame))
	}
	canvasProps.scale = scale
	canvasProps.translateX = 0
	canvasProps.translateY = 0
	await nextTick()
	const page = el.querySelector(".canvas")
	if (!page) return
	const origin = el.getBoundingClientRect().top
	const top =
		breakpoint.device === "mobile"
			? origin + (el.clientHeight - PHONE.height * scale) / 2
			: origin + PAD + (breakpoint.device === "tablet" ? PHONE.bezel : 0)
	canvasProps.translateY = (top - page.getBoundingClientRect().top) / scale
	fitted.value = true
}
// the canvas fits its own way first, as it mounts or switches breakpoint; this runs after it
const fitSoon = () => requestAnimationFrame(() => requestAnimationFrame(() => fit()))
watch(pageCanvas, fitSoon)
watch(device, fitSoon)
watch(
	() => store.settingPage,
	(setting) => !setting && fitSoon(),
)
useResizeObserver(room, useDebounceFn(fit, 50))

// the phone scrolls its own page, as a phone does, instead of panning the frame
useEventListener(
	room,
	"wheel",
	(event: WheelEvent) => {
		if (device.value !== "mobile" || event.ctrlKey || event.metaKey) return
		if ((event.target as Element).closest?.(".canvas")) event.stopPropagation()
	},
	{ capture: true },
)

const debouncedPageSave = useDebounceFn(store.savePage, 300)
watch(
	() => pageCanvas.value?.rootComponent,
	() => {
		if (
			store.selectedPage &&
			!pageCanvas.value?.canvasProps?.settingCanvas &&
			!store.settingPage &&
			!store.savingPage &&
			!store.pageConflict
		) {
			store.savingPage = true
			debouncedPageSave()
		}
	},
	{ deep: true },
)

let loadingPageID: string | null = null
async function loadPage(appID: string, pageID: string) {
	if (!pageID || pageID === "new" || pageID === store.selectedPage || loadingPageID === pageID) return
	loadingPageID = pageID
	try {
		if (store.activeApp?.name !== appID) await store.setApp(appID)
		await store.setPage(pageID)
	} catch (error) {
		console.error(`Failed to load page ${pageID}`, error)
		toast.error("Failed to load the page")
	} finally {
		loadingPageID = null
	}
}

watch(() => [props.appID, props.pageID], () => loadPage(props.appID, props.pageID), { immediate: true })

defineExpose({ loadPage })
</script>
