import { useStorage } from "@vueuse/core"

// the chat side panel, open beside any layer but the chat itself
export const assistantOpen = useStorage("frappe-assistant-open", false)
