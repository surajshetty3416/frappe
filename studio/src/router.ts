import type { App } from "vue"
import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router"

import type { Layer } from "./layer"
import { layers } from "./layers"
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

	const router = createRouter({
		history: createWebHistory(),
		routes: [
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
