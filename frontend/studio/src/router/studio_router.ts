import type { RouteLocationNormalizedLoaded, RouteLocationRaw, Router } from "vue-router"

// Studio navigates on the shell's router. A live binding: set by setupStudioRouter when the
// layer first opens, before any studio module navigates.
let router: Router
export { router as default }

export function setupStudioRouter(appRouter: Router) {
	router = appRouter
	resolveUnknownRoutesToNotFound(router)
}

// The canvas renders the edited app's router-links (e.g. `{ name: "Home" }`), whose routes the
// editor doesn't have. Resolve them to the not-found page instead of throwing, but only while
// studio is open, so every other layer keeps the router's own errors.
function resolveUnknownRoutesToNotFound(router: Router) {
	const resolve = router.resolve.bind(router)
	const notFound = (currentLocation?: RouteLocationNormalizedLoaded) =>
		resolve({ name: "StudioNotFound", params: { catchAll: "not-found" } }, currentLocation)

	router.resolve = (to: RouteLocationRaw, currentLocation?: RouteLocationNormalizedLoaded) => {
		if ((currentLocation ?? router.currentRoute.value).meta.layer !== "studio") {
			return resolve(to, currentLocation)
		}
		try {
			const resolved = resolve(to, currentLocation)
			return resolved.matched[0]?.meta.layer ? resolved : notFound(currentLocation)
		} catch {
			return notFound(currentLocation)
		}
	}
}
