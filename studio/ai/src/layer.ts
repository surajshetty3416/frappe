import { defineLayer } from "@shell/layer"

// The chat lives in the shell's chat column; this layer's own page waits for the Agents editor.
export default defineLayer({
	name: "ai",
	title: "Agents",
	icon: "lucide-bot",
	path: "/studio/ai",
	component: () => import("./App.vue"),
	routes: [
		{ path: "", redirect: "/studio" },
		{ path: "s/:session", redirect: (to) => `/studio/chat/${to.params.session}` },
	],
	setup: async () => {
		await import("./index.css")
	},
})
