import { reactive, computed, onMounted, onUnmounted } from "vue"

const MOBILE_BREAKPOINT = 576
const TABLET_BREAKPOINT = 768

export const breakpointAt = (width: number) => (width < MOBILE_BREAKPOINT ? "mobile" : width < TABLET_BREAKPOINT ? "tablet" : "desktop")

// the widest window each breakpoint's styles apply in
export const BREAKPOINT_MAX_WIDTH: Record<string, number> = {
	desktop: Infinity,
	tablet: TABLET_BREAKPOINT - 1,
	mobile: MOBILE_BREAKPOINT - 1,
}

export function useScreenSize() {
	const size = reactive({
		width: window.innerWidth,
		height: window.innerHeight,
	})

	const currentBreakpoint = computed(() => breakpointAt(size.width))

	const onResize = () => {
		size.width = window.innerWidth
		size.height = window.innerHeight
	}

	onMounted(() => {
		window.addEventListener("resize", onResize)
	})

	onUnmounted(() => {
		window.removeEventListener("resize", onResize)
	})

	return { size, currentBreakpoint }
}
