import { useStorage } from "@vueuse/core"
import { ref } from "vue"

export const layout = useStorage("studio-layout", {
	sidebarOpen: true,
	panelOpen: true,
	// the editor panel's share of the space beside the sidebar, in percent
	panelWidth: 60,
})

export const searchOpen = ref(false)
