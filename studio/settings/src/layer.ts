import { defineLayer } from "@shell/layer"

export default defineLayer({
	name: "settings",
	title: "Settings",
	icon: "lucide-settings",
	path: "/studio/settings",
	component: () => import("./App.vue"),
	routes: [
		{ path: "", redirect: { name: "settings", params: { section: "people" } } },
		{
			path: ":section(people|email|model|appearance)",
			name: "settings",
			component: () => import("./Settings.vue"),
		},
		{ path: ":unknown(.*)*", redirect: { name: "settings", params: { section: "people" } } },
	],
	setup: async () => {
		await import("./index.css")
	},
})
