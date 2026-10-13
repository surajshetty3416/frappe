import { defineLayer } from "@shell/layer";

import { setAppRouter, validateVisit } from "./router";

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
		{ path: "", name: "builder-home", component: () => import("./pages/PageBuilderDashboard.vue") },
		{ path: "home", redirect: { name: "builder-home" } },
		{ path: "page", redirect: { name: "builder-home" } },
		{
			path: "page/:pageId",
			name: "builder-editor",
			component: () => import("./studioEditor").then((editor) => editor.default.preview),
			meta: { artifact: { doctype: "Builder Page", param: "pageId", editor: () => import("./studioEditor") } },
		},
		{
			path: "page/:pageId/preview",
			name: "builder-preview",
			component: () => import("./pages/PagePreview.vue"),
		},
		{
			path: "persona-survey",
			name: "builder-persona-survey",
			component: () => import("./pages/PagePersonaSurvey.vue"),
		},
		// anything else under the layer (an old link, the editor demo's /studio/web/demo/<page>)
		{ path: ":unknown(.*)*", redirect: { name: "builder-home" } },
	],
	setup: async (app) => {
		setAppRouter(app.config.globalProperties.$router);
		const [{ registerGlobalComponents }] = await Promise.all([import("./globalComponents"), import("./index.css")]);
		registerGlobalComponents(app);
		window.name = "frappe-builder";
	},
	beforeEnter: validateVisit,
});
