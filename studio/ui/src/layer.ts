import { defineLayer } from "@shell/layer"
import session from "@ui/utils/session"

const artifact = { doctype: "Studio App", param: "appID" }

export default defineLayer({
	name: "ui",
	title: "Apps",
	icon: "lucide-blocks",
	path: "/studio/ui",
	component: () => import("./App.vue"),
	routes: [
		{ path: "", name: "StudioHome", component: () => import("./pages/Home.vue") },
		{
			path: "app/:appID",
			name: "StudioApp",
			component: () => import("./pages/StudioApp.vue"),
			meta: { artifact },
		},
		{
			path: "app/:appID/:pageID",
			name: "StudioPage",
			component: () => import("./pages/StudioPage.vue"),
			meta: { artifact },
		},
		{ path: "not-permitted", name: "StudioNotPermitted", component: () => import("./pages/NotPermitted.vue") },
		{
			path: ":catchAll(.*)",
			name: "StudioNotFound",
			component: () => import("./pages/NotFound.vue"),
			props: { home: "/studio/ui" },
		},
		// links from before the editor moved under /studio/ui
		{ path: "/studio/home", redirect: { name: "StudioHome" } },
		{ path: "/studio/app/:appID", redirect: { name: "StudioApp" } },
		{ path: "/studio/app/:appID/:pageID", redirect: { name: "StudioPage" } },
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
