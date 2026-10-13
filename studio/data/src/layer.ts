import { defineLayer } from "@shell/layer"

const artifact = { doctype: "DocType", param: "doctype", editor: () => import("./editor") }

export default defineLayer({
	name: "data",
	title: "Data",
	icon: "lucide-database",
	path: "/studio/data",
	component: () => import("./App.vue"),
	routes: [
		{ path: "", name: "data-schema", component: () => import("./pages/Schema.vue") },
		{
			path: "doctype/:doctype",
			name: "data-doctype",
			component: () => import("./editor").then((editor) => editor.default.preview),
			meta: { artifact },
		},
	],
	setup: async () => {
		await import("./index.css")
	},
})
