import { defineLayer } from "@shell/layer"
import session from "@studio/utils/session"

export default defineLayer({
	name: "studio",
	title: "Apps",
	icon: "lucide-blocks",
	path: "/studio",
	component: () => import("./App.vue"),
	routes: [
		{ path: "", redirect: { name: "StudioHome" } },
		{ path: "home", name: "StudioHome", component: () => import("./pages/Home.vue") },
		{ path: "app/:appID", name: "StudioApp", component: () => import("./pages/StudioApp.vue") },
		{ path: "app/:appID/:pageID", name: "StudioPage", component: () => import("./pages/StudioPage.vue") },
		{ path: "not-permitted", name: "StudioNotPermitted", component: () => import("./pages/NotPermitted.vue") },
		{ path: ":catchAll(.*)", name: "StudioNotFound", component: () => import("./pages/NotFound.vue") },
	],
	setup: async (app) => {
		const { default: setupStudio } = await import("./setup")
		setupStudio(app)
	},
	beforeEnter: async (to) => {
		await session.initialize()
		if (!session.hasPermission && to.name !== "StudioNotPermitted") return { name: "StudioNotPermitted" }
	},
})
