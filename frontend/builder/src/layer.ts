import { defineLayer } from "@shell/layer";

import { setAppRouter, validateVisit } from "./router";

export default defineLayer({
	name: "builder",
	title: "Websites",
	icon: "lucide-globe",
	// a site can serve the editor elsewhere (site config `builder_path`); read once the boot data is in
	get path() {
		return window.builder_path || "/builder";
	},
	component: () => import("./App.vue"),
	routes: [
		{ path: "", name: "builder-home", component: () => import("./pages/PageBuilderDashboard.vue") },
		{ path: "home", redirect: { name: "builder-home" } },
		{ path: "page", redirect: { name: "builder-home" } },
		{ path: "page/:pageId", name: "builder-editor", component: () => import("./pages/PageBuilder.vue") },
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
		// anything else under /builder (an old link, the editor demo's /builder/demo/<page>)
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
