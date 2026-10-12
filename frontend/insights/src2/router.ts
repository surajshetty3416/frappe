import type { Router } from 'vue-router'

// The app's one router belongs to the shell. The layer's setup hands it over, and
// the binding is live, so a module that imports it before then still navigates.
let router: Router

export function setAppRouter(appRouter: Router) {
	router = appRouter
}

export { router as default }
