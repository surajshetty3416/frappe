import { defineLayer } from "@shell/layer";

import { validateVisit } from "./router";

export default defineLayer({
	name: "web",
	title: "Websites",
	icon: "lucide-globe",
	// site config `builder_path` can move the layer elsewhere under /studio; read once the boot data is in
	get path() {
		return window.builder_path || "/studio/web";
	},
	component: () => import("./App.vue"),
	routes: [
		{ path: "", name: "builder-home", component: () => import("./pages/WebPages.vue") },
		{
			path: "page/:pageId",
			name: "builder-editor",
			component: () => import("./studioEditor").then((editor) => editor.default.preview),
			meta: { artifact: { doctype: "Builder Page", param: "pageId", editor: () => import("./studioEditor") } },
		},
		// anything else under the layer, such as an old link
		{ path: ":unknown(.*)*", redirect: { name: "builder-home" } },
	],
	setup: async () => {
		await import("./index.css");
	},
	beforeEnter: validateVisit,
});
