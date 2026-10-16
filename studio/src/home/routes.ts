import type { NavigationGuard, RouteRecordRaw } from "vue-router"

// the home's pages, drawn in its own shell; `setUpLayers` readies the chat its pane holds and the charts its widgets draw
export const homeRoutes = (setUpLayers: NavigationGuard): RouteRecordRaw[] =>
	[
		{ path: "/home", name: "home", component: () => import("./HomePage.vue") },
		{ path: "/home/setup", name: "home-setup", component: () => import("./SetupPage.vue") },
		{ path: "/home/:kind(apps|websites|dashboards)", name: "home-kind", component: () => import("./KindPage.vue") },
		{ path: "/home/:kind(apps|websites|dashboards)/:name", name: "home-view", component: () => import("./ViewPage.vue") },
	].map((route) => ({ ...route, meta: { layer: "ai", home: true }, beforeEnter: setUpLayers }))
