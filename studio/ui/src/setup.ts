import "./index.css"

import type { App } from "vue"
import { COMPONENTS } from "@ui/data/components"
import Block from "@ui/utils/block"
import { registerGlobalComponents } from "@ui/globals"
import { setupStudioRouter } from "@ui/router/studio_router"
import { initSocket } from "@ui/socket"

// Runs once, the first time someone opens the studio layer
export default function setupStudio(app: App) {
	Block.setComponents(COMPONENTS)
	registerGlobalComponents(app)
	// the canvas resolves the edited app's components from the app's global registry
	window.__APP_COMPONENTS__ = app._context.components
	setupStudioRouter(app.config.globalProperties.$router)
	initSocket()
}
