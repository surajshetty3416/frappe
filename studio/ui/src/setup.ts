import "./index.css"

import type { App, Component } from "vue"
import { COMPONENTS } from "@ui/data/components"
import Block from "@ui/utils/block"
import { registerGlobalComponents } from "@ui/globals"
import { setupStudioRouter } from "@ui/router/studio_router"
import { initSocket } from "@ui/socket"

// Runs once, the first time someone opens the studio layer
export default function setupStudio(app: App) {
	Block.setComponents(COMPONENTS)
	// the canvas resolves the edited app's components from its own registry: on the shell's app,
	// "Button" would also answer every other layer's <component is="button">
	const components: Record<string, Component> = {}
	registerGlobalComponents({ component: (name: string, component?: Component) => (component ? (components[name] = component) : components[name]) } as App)
	window.__APP_COMPONENTS__ = components
	setupStudioRouter(app.config.globalProperties.$router)
	initSocket()
}
