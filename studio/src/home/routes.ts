import type { NavigationGuard, RouteRecordRaw } from "vue-router"

// the home's pages, drawn in its own shell; `setUpChat` readies the chat its pane holds
export const homeRoutes = (setUpChat: NavigationGuard): RouteRecordRaw[] =>
	[
		{ path: "/home", name: "home", component: () => import("./HomePage.vue") },
		{ path: "/home/:kind(apps|websites|dashboards)", name: "home-kind", component: () => import("./KindPage.vue") },
		{ path: "/home/:kind(apps|websites|dashboards)/:name", name: "home-view", component: () => import("./ViewPage.vue") },
	].map((route) => ({ ...route, meta: { layer: "ai", home: true }, beforeEnter: setUpChat }))
