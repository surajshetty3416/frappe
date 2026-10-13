import { defineLayer } from "@shell/layer"

const agent = { doctype: "Flow Agent", param: "agent", editor: () => import("./agent/editor") }
const automation = { doctype: "Automation Flow", param: "automation", editor: () => import("./automation/editor") }

export default defineLayer({
	name: "agents",
	title: "Agents",
	icon: "lucide-bot",
	path: "/studio/agents",
	component: () => import("./App.vue"),
	routes: [
		{ path: "", name: "agents-home", component: () => import("./pages/Home.vue") },
		{
			path: "agent/:agent",
			name: "agents-agent",
			component: () => import("./agent/editor").then((editor) => editor.default.preview),
			meta: { artifact: agent },
		},
		{
			path: "automation/:automation",
			name: "agents-automation",
			component: () => import("./automation/editor").then((editor) => editor.default.preview),
			meta: { artifact: automation },
		},
	],
	setup: async () => {
		await import("./index.css")
	},
})
