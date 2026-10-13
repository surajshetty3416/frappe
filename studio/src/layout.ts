import { useStorage } from "@vueuse/core"
import { ref } from "vue"

export const layout = useStorage("studio-layout", {
	sidebarOpen: true,
	panelOpen: true,
	// the editor panel's share of the space beside the sidebar, in percent
	panelWidth: 60,
})

export const searchOpen = ref(false)

// a menu, popover or dialog is open over the page; it takes Esc before the shell does
export const overlayOpen = () =>
	Boolean(document.querySelector("[data-reka-popper-content-wrapper]:not(:has([role=tooltip])), [role=dialog]"))
