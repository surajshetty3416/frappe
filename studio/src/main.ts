import { FrappeUI, frappeRequest, setConfig } from "frappe-ui"
import { createPinia } from "pinia"
import { createApp } from "vue"

import App from "./App.vue"
import "./index.css"
import { createAppRouter } from "./router"
import translation from "./translation"

setConfig("resourceFetcher", frappeRequest)

// the server renders boot data into the page; the Vite dev server has no page template
async function loadDevBoot() {
	const response = await fetch("/api/method/frappe.www._frontend.get_context_for_dev", { method: "POST" })
	Object.assign(window, (await response.json()).message)
}

async function mount() {
	if (import.meta.env.DEV) await loadDevBoot()
	const app = createApp(App)
	app.use(createPinia())
	app.use(FrappeUI, { resources: true })
	app.use(translation)
	app.use(createAppRouter(app))
	app.mount("#app")
}

mount()
