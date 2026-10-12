import type { App } from 'vue'
import { registerControllers } from './controllers'
import { registerGlobalComponents } from './globals'
import { setRouter } from './helpers/navigation'
import './index.css'
import { setAppRouter } from './router'

// The layer's setup: the shell has created the app, its router and its providers,
// and runs this once, the first time someone opens Insights.
export default function setup(app: App) {
	const router = app.config.globalProperties.$router
	setAppRouter(router)
	setRouter({
		resolveHref: (to) => router.resolve(to).href,
		navigate: (to) => router.push(to),
	})
	registerGlobalComponents(app)
	registerControllers(app)
}
