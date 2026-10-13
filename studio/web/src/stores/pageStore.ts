import type Block from "@web/block";
import { builderSettings } from "@web/data/builderSettings";
import { webPages } from "@web/data/webPage";
import useCanvasStore from "@web/stores/canvasStore";
import useComponentStore from "@web/stores/componentStore";
import { BuilderClientScript, BuilderPage } from "@web/types/doctypes";
import getBlockTemplate from "@web/utils/blockTemplate";
import { generateId, getBlockInstance, getCopyWithoutParent } from "@web/utils/helpers";
import { createDocumentResource, createListResource, toast } from "frappe-ui";
import { defineStore } from "pinia";

/** Normalize query values to strings; repeated parameters use the first value. */
function normalizeRouteVariables(values: unknown) {
	if (!values || typeof values !== "object" || Array.isArray(values)) {
		return {};
	}
	const entries = Object.entries(values).map(([key, value]) => [
		key,
		String((Array.isArray(value) ? value[0] : value) ?? ""),
	]);
	return Object.fromEntries(entries) as { [key: string]: string };
}

const usePageStore = defineStore("pageStore", {
	state: () => ({
		routeVariables: <{ [key: string]: string }>{},
		pageData: <{ [key: string]: [] }>{},
		selectedPage: <string | null>null,
		pageBlocks: <Block[]>[],
		saveId: null as string | null,
		activePage: <BuilderPage | null>null,
		activePageScripts: <BuilderClientScript[]>[],
		savingPage: false,
		settingPage: false,
		pageLoadToken: 0,
	}),
	actions: {
		async setPage(pageName: string, routeParams = null as Record<string, unknown> | null) {
			if (!pageName) return;
			this.settingPage = true;
			this.selectedPage = pageName;
			const pageLoadToken = ++this.pageLoadToken;

			const page = await this.fetchActivePage(pageName);
			if (pageLoadToken !== this.pageLoadToken || this.selectedPage !== pageName) return;
			if (!page) {
				toast.error("Page not found");
				return;
			}
			this.activePage = page;
			const blocks = JSON.parse(page.draft_blocks || page.blocks || "[]");
			this.pageBlocks = [getBlockInstance(blocks[0] || getBlockTemplate("body"))];
			this.loadRouteVariables(page.name, routeParams);
			await this.setPageData(page);
			useCanvasStore().activeCanvas?.setRootBlock(this.pageBlocks[0]);

			if (page.client_scripts?.length) {
				const scripts = createListResource({
					doctype: "Builder Client Script",
					fields: ["script_type", "name", "script"],
					filters: [["name", "in", page.client_scripts.map((script) => script.builder_script)]],
					auto: true,
				});
				await scripts.list.promise;
				this.activePageScripts = scripts.data as BuilderClientScript[];
			} else {
				this.activePageScripts = [];
			}

			// components a page uses load on their own; the page shows once they are in
			const componentStore = useComponentStore();
			const interval = setInterval(() => {
				if (componentStore.fetchingComponent.size) return;
				clearInterval(interval);
				if (pageLoadToken === this.pageLoadToken) this.settingPage = false;
			}, 50);
		},

		loadRouteVariables(pageName: string, routeParams: Record<string, unknown> | null = null) {
			const stored = localStorage.getItem(`${pageName}:routeVariables`) || "{}";
			this.routeVariables = normalizeRouteVariables(JSON.parse(stored));
			if (routeParams) {
				Object.assign(this.routeVariables, normalizeRouteVariables(routeParams));
			}
		},

		async fetchActivePage(pageName: string) {
			const resource = createDocumentResource({ doctype: "Builder Page", name: pageName, auto: true });
			try {
				await resource.get.promise;
			} catch (e) {
				return null;
			}
			return resource.doc as BuilderPage;
		},

		async publishPage() {
			await this.waitTillPageIsSaved();
			await webPages.runDocMethod.submit({
				name: this.selectedPage as string,
				method: "publish",
				route_variables: this.routeVariables,
			});
			this.activePage = await this.fetchActivePage(this.selectedPage as string);
		},

		updateActivePage(key: keyof BuilderPage, value: any) {
			if (!this.activePage) return;
			// update in place so reactive bindings stay consistent
			this.activePage[key] = value;
			return webPages.setValue.submit({ name: this.activePage.name as string, [key]: value });
		},

		savePage() {
			this.savingPage = true;
			const root = useCanvasStore().activeCanvas?.getRootBlock();
			const saveId = generateId();
			// more saves can start before the first one completes
			this.saveId = saveId;
			return webPages.setValue
				.submit({
					name: this.activePage?.name || this.selectedPage,
					draft_blocks: JSON.stringify(root ? [getCopyWithoutParent(root)] : []),
				})
				.then((page: BuilderPage) => {
					if (this.activePage) Object.assign(this.activePage, page);
					else this.activePage = page;
				})
				.finally(() => {
					if (this.saveId !== saveId) return;
					this.saveId = null;
					this.savingPage = false;
				});
		},

		setPageData(page?: BuilderPage) {
			if (!page || !page.page_data_script) {
				this.pageData = {};
				return;
			}
			return webPages.runDocMethod
				.submit({ method: "get_page_data", name: page.name, route_variables: this.routeVariables })
				.then((data: { message: { [key: string]: [] } }) => {
					this.pageData = data.message;
				})
				.catch((e: { exc: string | null }) => {
					toast.error("The page's data script failed", { description: e.exc?.split("\n").slice(-2)[0] });
				});
		},

		async waitTillPageIsSaved() {
			// a short delay so that every pending save has started
			if (!this.savingPage) await new Promise((resolve) => setTimeout(resolve, 300));
			return new Promise((resolve) => {
				const interval = setInterval(() => {
					if (this.savingPage) return;
					clearInterval(interval);
					resolve(null);
				}, 100);
			});
		},

		isHomePage(page: BuilderPage | null = null) {
			return builderSettings.doc?.home_page === (page || this.activePage)?.route;
		},
	},
});

export default usePageStore;
