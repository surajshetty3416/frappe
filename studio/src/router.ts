import type { App } from "vue"
import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router"

import type { Layer } from "./layer"
import { layers } from "./layers"
import { homeRoutes } from "./home/routes"
import { keepLayerLinksInApp } from "./links"
import { isLoggedIn } from "./session"

export function createAppRouter(app: App) {
	const setups = new Map<string, Promise<void>>()
	const setUp = (layer: Layer) => {
		if (!setups.has(layer.name)) setups.set(layer.name, Promise.resolve(layer.setup?.(app)))
		return setups.get(layer.name)
	}

	const layerRoute = (layer: Layer): RouteRecordRaw => ({
		path: layer.path,
		component: layer.component,
		meta: { layer: layer.name },
		beforeEnter: [async () => void (await setUp(layer)), ...(layer.beforeEnter ? [layer.beforeEnter] : [])],
		children: layer.routes,
	})

	// Studio starts from its chat, in a project; the home, a project, the lists of what was made and
	// the chats are the shell's own pages, the home and a project drawn around a new chat
	const aiLayer = layers.find((layer) => layer.name === "ai")
	const withChat = { meta: { layer: "ai" }, beforeEnter: async () => void (aiLayer && (await setUp(aiLayer))) }
	const analyticsLayer = layers.find((layer) => layer.name === "analytics")
	const studioRoutes: RouteRecordRaw[] = [
		{ path: "/studio", name: "studio-home", component: () => import("./pages/ChatPane.vue"), ...withChat },
		{
			path: "/studio/project/:project/:tab(artifacts|skills)?",
			name: "studio-project",
			component: () => import("./pages/ChatPane.vue"),
			...withChat,
		},
		{
			path: "/studio/:kind(apps|websites|dashboards)",
			name: "studio-artifacts",
			component: () => import("./pages/Artifacts.vue"),
		},
		{
			path: "/studio/chat/:session",
			name: "studio-chat",
			component: () => import("./pages/ChatPane.vue"),
			meta: withChat.meta,
			// a new chat, which a layer starts with its first message, is the home's
			beforeEnter: [
				(to) => (to.params.session === "new" ? { name: "studio-home", query: to.query } : undefined),
				withChat.beforeEnter,
			],
		},
		...homeRoutes(async () => {
			await withChat.beforeEnter()
			if (analyticsLayer) await setUp(analyticsLayer)
		}),
		// the app editor's addresses before it moved under /studio/ui
		{ path: "/studio/home", redirect: "/studio/ui" },
		{ path: "/studio/app/:rest(.*)", redirect: (to) => `/studio/ui/app/${to.params.rest}` },
	]

	const router = createRouter({
		history: createWebHistory(),
		routes: [
			...studioRoutes,
			...layers.map(layerRoute),
			{
				// anything else (the desk, a website page) is the server's to render
				path: "/:outside(.*)*",
				component: { render: () => null },
				beforeEnter: (to) => {
					window.location.href = to.fullPath
					return false
				},
			},
		],
	})

	router.beforeEach((to) => {
		if (isLoggedIn() || to.matched.some((record) => record.meta.guest)) return
		window.location.href = `/login?redirect-to=${encodeURIComponent(to.fullPath)}`
		return false
	})
	router.afterEach((to) => {
		const layer = to.matched[0]?.meta.layer
		if (typeof layer === "string") document.documentElement.dataset.layer = layer
	})
	keepLayerLinksInApp(router)
	return router
}
