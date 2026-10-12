import "@ui/renderer.css"

import { createApp } from "vue"
import { createPinia } from "pinia"
import "@ui/setupFrappeUIResource"
import { createAppRouter } from "@ui/router/app_router"
import ErrorPage from "@ui/pages/ErrorPage.vue"
import AppRenderer from "@ui/AppRenderer.vue"
import { resourcesPlugin } from "frappe-ui"
import { registerGlobalComponents, registerCustomVueComponents } from "@ui/globals"
import { registerStudioPageScripts } from "@ui/data/studioPageScripts"
import { initSocket } from "@ui/socket"

// For rendering apps built by studio
const app = createApp(AppRenderer)
const pinia = createPinia()

app.use(pinia)
app.use(resourcesPlugin)
app.provide("socket", initSocket())
registerGlobalComponents(app)
window.__APP_COMPONENTS__ = app._context.components

const frappeApp = (window as any).frappe_app
const componentsReady = frappeApp
	? Promise.all([registerCustomVueComponents(frappeApp), registerStudioPageScripts(frappeApp)])
	: Promise.resolve()

componentsReady
	.then(() => createAppRouter())
	.then((router) => app.use(router).mount("#app"))
	.catch((error) => {
		console.error(error)
		createApp(ErrorPage, { error }).mount("#app")
	})
