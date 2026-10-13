import { defineLayer } from "@shell/layer"

const artifact = { doctype: "Email Template", param: "template", editor: () => import("./editor") }

export default defineLayer({
	name: "email",
	title: "Email",
	icon: "lucide-mail",
	path: "/studio/email",
	component: () => import("./App.vue"),
	routes: [
		{ path: "", name: "email-home", component: () => import("./pages/Emails.vue") },
		{
			path: "template/:template/:record?",
			name: "email-template",
			component: () => import("./editor").then((editor) => editor.default.preview),
			meta: { artifact },
		},
	],
	setup: async () => {
		await import("./index.css")
	},
})
