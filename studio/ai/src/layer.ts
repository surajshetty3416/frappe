import { defineLayer } from "@shell/layer"

// The chat page is one view; its routes only name the open conversation.
const conversation = { render: () => null }

export default defineLayer({
	name: "ai",
	title: "Agents",
	icon: "lucide-bot",
	path: "/studio/ai",
	component: () => import("./App.vue"),
	routes: [
		{ path: "", name: "ai-home", component: conversation },
		{ path: "s/:session", name: "ai-session", component: conversation },
	],
	setup: async () => {
		await import("./index.css")
	},
})
