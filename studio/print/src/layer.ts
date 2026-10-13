import { defineLayer } from "@shell/layer"

const artifact = { doctype: "Print Format", param: "format", editor: () => import("./editor") }

export default defineLayer({
	name: "print",
	title: "Print",
	icon: "lucide-printer",
	path: "/studio/print",
	component: () => import("./App.vue"),
	routes: [
		{ path: "", name: "print-home", component: () => import("./pages/PrintFormats.vue") },
		{
			path: "format/:format/:record?",
			name: "print-format",
			component: () => import("./editor").then((editor) => editor.default.preview),
			meta: { artifact },
		},
	],
	setup: async () => {
		await import("./index.css")
	},
})
