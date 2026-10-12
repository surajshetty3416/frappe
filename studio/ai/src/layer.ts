import { defineLayer } from "@shell/layer"

// The chat page is one view; its routes only name the open conversation.
const conversation = { render: () => null }

export default defineLayer({
	name: "flow",
	title: "Chat",
	icon: "lucide-message-circle",
	path: "/flow",
	component: () => import("./App.vue"),
	routes: [
		{ path: "", name: "flow-new", component: conversation },
		{ path: "s/:session", name: "flow-session", component: conversation },
	],
	setup: async () => {
		await import("./index.css")
	},
})
