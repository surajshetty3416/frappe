import { ref, nextTick, computed, toRaw, readonly } from "vue"
import { useDebounceFn } from "@vueuse/core"
import router from "@ui/router/studio_router"
import { defineStore } from "pinia"

import { fetchApp, fetchPage, confirm, getInitialVariableValue, getRouteVariables } from "@ui/utils/helpers"
import { getBlockInstance, getRootBlock, getBlockCopyWithoutParent, jsToJson } from "@ui/utils/serializer"
import { studioPages } from "@ui/data/studioPages"
import { studioApps } from "@ui/data/studioApps"
import { studioVariables } from "@ui/data/studioVariables"

import Block from "@ui/utils/block"
import useCanvasStore from "@ui/stores/canvasStore"
import useCodeStore, { usePageScope } from "@ui/stores/codeStore"
import { reloadCustomVueComponents } from "@ui/globals"
import { registerStudioPageScripts, unregisterStudioPageScripts } from "@ui/data/studioPageScripts"
import { registerCustomComponentPaths } from "@ui/utils/components"
import type { CustomVueComponentMeta } from "@ui/types/vue"

import type { StudioApp } from "@ui/types/Studio/StudioApp"
import type { StudioPage } from "@ui/types/Studio/StudioPage"
import type { Variable, VariableOption } from "@ui/types/Studio/StudioPageVariable"
import { toast, dialog } from "frappe-ui"
import { call } from "frappe-ui"

type PageFields = Partial<Pick<StudioPage, "page_title" | "route" | "script" | "allow_guest">>

const PAGE_CHANGED_MESSAGE = "This page was changed outside the editor. Refresh to load the latest version."

const useStudioStore = defineStore("studioStore", () => {
	// studio apps
	const activeApp = ref<StudioApp | null>(null)
	const appPages = computed<Record<string, StudioPage>>(() => {
		const pages: Record<string, StudioPage> = {}
		studioPages.data?.forEach((page: StudioPage) => {
			pages[page.name] = page
		})
		return pages
	})
	const customVueComponents = ref<CustomVueComponentMeta[]>([])

	async function setApp(appName: string) {
		const appDoc = await fetchApp(appName)
		if (!appDoc) return
		activeApp.value = appDoc
		await setAppBoot(appName)
		await setAppPages(appName)
		await setCustomComponents()
		await setupPageScripts()
	}

	// the canvas is not a rendered app page, so it asks for the app's studio_app_boot dict
	async function setAppBoot(appName: string) {
		try {
			window.boot = await call("frappe.ui.api.get_app_boot", { app_name: appName })
		} catch (error) {
			console.error("Failed to load app boot", error)
			window.boot = {}
		}
	}

	async function deleteApp(appName: string, appTitle: string) {
		if (!appName) return
		const confirmed = await confirm(`Are you sure you want to delete the app "${appTitle}"?`)
		if (confirmed) {
			studioApps.delete.submit(appName, {
				onSuccess() {
					if (activeApp.value?.name === appName) {
						router.replace({ name: "StudioHome" })
					}
					toast.success(`App "${appTitle}" deleted`)
				},
				onError() {
					toast.error("An unexpected error occurred while deleting the app.")
				},
			})
		}
	}

	async function setAppPages(appName: string) {
		if (!appName) {
			return
		}
		studioPages.filters = { studio_app: appName }
		await studioPages.reload()
	}

	function updateActiveApp(key: string, value: string) {
		return studioApps.setValue.submit(
			{ name: activeApp.value?.name, [key]: value },
			{
				onSuccess() {
					setApp(activeApp.value!.name)
				},
			},
		)
	}

	// a new page opens at once, like the old New Page link
	function createPage(appName: string): Promise<StudioPage> {
		return studioPages.insert.submit({ draft_blocks: [getRootBlock()], studio_app: appName })
	}

	function getAppPageRoute(pageName: string) {
		return Object.values(appPages.value).find((page) => page.name === pageName)?.route
	}

	// studio pages
	const activePage = ref<StudioPage | null>(null)
	const pageBlocks = ref<Block[]>([])
	const selectedPage = ref<string | null>(null)
	const savingPage = ref(false)
	const publishingApp = ref(false)
	const settingPage = ref(false)
	// set when a save is rejected because the page moved on in the DB (a disk sync or an AI edit)
	// after the editor loaded it. Autosave pauses until the user refreshes to the latest version.
	const pageConflict = ref(false)

	// design-time test values for dynamic route variables (e.g. { category: "tech" }), persists in localStorage
	const routeVariables = ref<Record<string, string>>({})

	async function setPage(pageName: string) {
		settingPage.value = true
		pageConflict.value = false
		savingPage.value = false
		pageScope.teardownPage()

		const page = await fetchPage(pageName)
		if (!page) {
			settingPage.value = false
			return
		}
		activePage.value = page
		loadRouteVariables(page)
		await seedRouteVariables(page)
		await setPageData(page)
		await pageScope.setPageScript(page, Boolean(page.is_standard))

		const blocks = JSON.parse(page.draft_blocks || page.blocks || "[]")
		if (blocks.length === 0) {
			pageBlocks.value = [getRootBlock()]
		} else {
			pageBlocks.value = [getBlockInstance(blocks[0])]
		}
		selectedPage.value = page.name

		const canvasStore = useCanvasStore()
		canvasStore.activeCanvas?.setRootBlock(pageBlocks.value[0])
		canvasStore.activeCanvas?.clearSelection()

		nextTick(() => {
			settingPage.value = false
		})
	}

	function savePage(rootBlock?: Block) {
		if (rootBlock) {
			pageBlocks.value = [rootBlock]
		} else {
			const canvasStore = useCanvasStore()
			if (canvasStore?.activeCanvas) {
				pageBlocks.value = [canvasStore.activeCanvas.getRootBlock()]
			}
		}
		const pageData = jsToJson(pageBlocks.value.map((block) => getBlockCopyWithoutParent(block)))
		const savedPage = selectedPage.value

		return studioPages.runDocMethod
			.submit({
				name: savedPage,
				method: "save_draft",
				draft_blocks: pageData,
				known_modified: activePage.value?.modified,
			})
			.then((response: any) => {
				// a save that resolves after the user switched pages must not stamp this page's
				// timestamp/draft marker onto the newly opened one
				if (activePage.value?.name !== savedPage) return
				syncPageModified(response)
				// track that the page now has unpublished changes (drives the "Revert Changes" option)
				activePage.value.draft_blocks = pageData
			})
			.catch(handlePageWriteConflict)
			.finally(() => {
				if (activePage.value?.name === savedPage) savingPage.value = false
			})
	}

	function syncPageModified(response: any) {
		const modified = response?.docs?.[0]?.modified ?? response?.modified ?? response?.message
		if (activePage.value && modified) activePage.value.modified = modified
	}

	async function refreshActivePageModified() {
		const pageName = activePage.value?.name
		if (!pageName) return
		const page = await call("frappe.client.get_value", {
			doctype: "Studio Page",
			filters: pageName,
			fieldname: "modified",
		})
		if (activePage.value?.name === pageName) syncPageModified(page)
	}

	function handlePageWriteConflict(error: any) {
		if (error?.exc_type === "TimestampMismatchError") {
			if (pageConflict.value) return
			pageConflict.value = true
			dialog.confirm({
				title: "Page changed outside the editor",
				message:
					"This page was updated after you opened it. Refresh to load the latest version - your unsaved canvas changes will be replaced.",
				confirmLabel: "Refresh",
				theme: "amber",
				onConfirm: () => selectedPage.value && setPage(selectedPage.value),
			})
		} else throw error
	}

	// resolves to false when the page changed elsewhere: the conflict prompt takes it from there
	function updateActivePage(key: string, value: string | number): Promise<boolean> | undefined {
		return saveActivePage({ [key]: value } as PageFields)
	}

	function saveActivePage(values: PageFields): Promise<boolean> | undefined {
		if (!activePage.value) return
		const page = activePage.value
		return savePageFields(page, values)
			.then((response: any) => {
				if (activePage.value?.name !== page.name) return true
				Object.assign(activePage.value, values)
				syncPageModified(response)
				return true
			})
			.catch((error: any) => {
				handlePageWriteConflict(error)
				return false
			})
	}

	// saves the fields together, and rejects when the page changed after it was loaded instead of
	// overwriting the newer version
	async function updatePage(page: StudioPage, values: PageFields) {
		if (activePage.value?.name === page.name) {
			if (!(await saveActivePage(values))) throw new Error(PAGE_CHANGED_MESSAGE)
		} else {
			await savePageFields(page, values).catch(async (error: any) => {
				await studioPages.reload()
				throw error
			})
		}
		await studioPages.reload()
	}

	function savePageFields(page: StudioPage, values: PageFields) {
		return studioPages.runDocMethod.submit({
			name: page.name,
			method: "save_page_field",
			fieldname: values,
			known_modified: page.modified,
		})
	}

	// the open page's flag can be newer than its row in the pages list
	function pageAllowsGuests(page: StudioPage) {
		const isActive = activePage.value?.name === page.name
		return Boolean(isActive ? activePage.value?.allow_guest : page.allow_guest)
	}

	// A server tool (AI) wrote the page script straight to the DB / code file, so re-fetch the
	// page and re-run setup() on the canvas. (Standard pages update only after their app rebuilds.)
	async function reloadActiveAppRouterScript() {
		if (!activeApp.value) return
		const app = await fetchApp(activeApp.value.name)
		if (app && activeApp.value?.name === app.name) activeApp.value.router_script = app.router_script
	}

	async function reloadActivePageScript() {
		if (!activePage.value) return
		const page = await fetchPage(activePage.value.name)
		if (!page) return
		activePage.value = page
		await pageScope.setPageScript(page, Boolean(page.is_standard))
	}

	async function publishApp() {
		if (!activeApp.value || publishingApp.value) return
		publishingApp.value = true
		return studioApps.runDocMethod.submit(
			{
				name: activeApp.value.name,
				method: "publish_app",
			},
			{
				async onSuccess(data: any) {
					activePage.value = await fetchPage(selectedPage.value!)
					setAppPages(activeApp.value!.name)
					if (data?.message?.build_error) {
						toast.warning("Published, but the build failed", {
							description: "Published pages may not show your latest changes.",
						})
					} else {
						toast.success("Published")
					}
				},
				onError(error: any) {
					toast.error("Failed to publish the app", {
						description: error?.messages?.join(", "),
					})
				},
			},
		)
		.finally(() => (publishingApp.value = false))
	}

	async function unpublishApp() {
		if (!activeApp.value) return
		const confirmed = await confirm(
			`Unpublish "${activeApp.value.app_title}"? Its pages will no longer be available.`,
		)
		if (!confirmed) {
			return
		}
		return studioApps.runDocMethod.submit(
			{
				name: activeApp.value.name,
				method: "unpublish_app",
			},
			{
				onSuccess() {
					setAppPages(activeApp.value!.name)
					toast.success("App unpublished")
				},
				onError(error: any) {
					toast.error("Failed to unpublish the app", {
						description: error?.messages?.join(", "),
					})
				},
			},
		)
	}

	let previewTab: Window | null = null
	// the published page, where a person signs in as one of the app's users
	function openPage() {
		if (!activeApp.value || !activePage.value) return
		let route = `/${activeApp.value.route}${resolveRouteVariables(activePage.value.route)}`
		if (import.meta.env.DEV) {
			route = `${window.site_url}${route}`
		}

		// a fresh tab opens in front; navigating a reused named tab leaves it in the background
		const nextTab = window.open(route, "_blank")
		if (nextTab) {
			previewTab?.close()
			previewTab = nextTab
		}
	}

	// substitute test route variables set by the user into the dynamic route so preview opens the concrete URL,
	// e.g. "/notes/:id" + { id: "note-1" } -> "/notes/note-1" (unset params keep their placeholder)
	function resolveRouteVariables(route: string) {
		return getRouteVariables(route).reduce((resolved, name) => {
			const value = routeVariables.value[name]
			return value ? resolved.replace(`:${name}`, encodeURIComponent(value)) : resolved
		}, route)
	}

	// custom components
	async function setCustomComponents() {
		await loadCustomVueComponents()
		await registerCustomComponentPaths(customVueComponents.value)
	}

	async function loadCustomVueComponents() {
		const frappeApp = activeApp.value?.is_standard ? activeApp.value.frappe_app! : ""
		customVueComponents.value = await reloadCustomVueComponents(frappeApp)
	}

	// Register per-page code scripts (<page>.ts) for exported apps so the editor can load them.
	async function setupPageScripts() {
		unregisterStudioPageScripts()
		if (activeApp.value?.is_standard) {
			await registerStudioPageScripts(activeApp.value.frappe_app!)
		}
	}

	// data
	const routeObject = computed(() => {
		if (!activePage.value) return ""

		// copy — mutating the live route object would wipe the editor router's own params (appID/pageID)
		const newRoute = { ...toRaw(router.currentRoute.value) }
		// Seed each dynamic param with its design-time test value (empty string when unset),
		// e.g. "/hr/:employee/:id" -> { employee, id } filled from routeVariables
		const paramNames = getRouteVariables(activePage.value.route)
		newRoute.params = paramNames.reduce(
			(params, name) => {
				params[name] = routeVariables.value[name] ?? ""
				return params
			},
			{} as Record<string, string>,
		)

		return newRoute
	})

	// route variables on the active page that have no test value yet — used to nudge the user, since
	// unset variables render the page's empty state (no doc / no rows) which can look like a bug
	const areRouteVariablesSet = computed(() => {
		if (!activePage.value) return true
		return getRouteVariables(activePage.value.route).every((name) => !!routeVariables.value[name])
	})

	function loadRouteVariables(page: StudioPage) {
		const key = `${page.name}:routeVariables`
		try {
			const stored = localStorage.getItem(key)
			const parsed = stored ? JSON.parse(stored) : null
			routeVariables.value = parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : {}
		} catch (error) {
			console.error(`Failed to parse route variables for ${page.name}, resetting`, error)
			routeVariables.value = {}
			localStorage.removeItem(key)
		}
	}

	// a route variable without a test value takes the first record the screen would open on: the first
	// row of the list that links to it, or else the first record the page looks it up in
	async function seedRouteVariables(page: StudioPage) {
		const unset = new Set(getRouteVariables(page.route).filter((name) => !routeVariables.value[name]))
		for (const resource of page.resources || []) {
			if (!unset.size) return
			if (resource.resource_type !== "Document" || !resource.fetch_document_using_filters || !resource.filters) continue
			const filters = parseFilters(resource.filters)
			for (const [field, value] of Object.entries(filters)) {
				const name = typeof value === "string" ? value.match(/^\{\{\s*route\.params\.(\w+)\s*\}\}$/)?.[1] : null
				if (!name || !unset.has(name)) continue
				unset.delete(name)
				const testValue =
					(await getFirstListedValue(page, resource.document_type, name)) ??
					(await getFirstValue(resource.document_type, field))
				if (testValue && activePage.value?.name === page.name) routeVariables.value[name] = String(testValue)
			}
		}
	}

	const parseFilters = (filters: unknown) => (typeof filters === "string" ? JSON.parse(filters) : filters || {}) as Record<string, unknown>

	// the first row of another page's list whose rows route to this page, in the list's filter and order;
	// filters on page variables are left out, as those start empty
	async function getFirstListedValue(page: StudioPage, doctype: string, variable: string) {
		const escape = (text: string) => text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
		const routePattern = page.route
			.split("/")
			.map((part) => (part === `:${variable}` ? "\\{\\{\\s*\\w+\\.(\\w+)\\s*\\}\\}" : part.startsWith(":") ? "\\{\\{[^}]*\\}\\}" : escape(part)))
			.join("/")
		const linkPattern = new RegExp(`"route":\\s*"${routePattern}"`)
		for (const sibling of Object.values(appPages.value)) {
			if (sibling.name === page.name) continue
			const doc = await fetchPage(sibling.name)
			const field = String(doc?.draft_blocks || doc?.blocks || "").match(linkPattern)?.[1]
			const list = field && doc.resources?.find((resource: any) => resource.resource_type === "Document List" && resource.document_type === doctype)
			if (!list) continue
			const filters = Object.fromEntries(Object.entries(parseFilters(list.filters)).filter(([, value]) => !JSON.stringify(value).includes("{{")))
			return getFirstValue(doctype, field, filters, list.sort_field && `${list.sort_field} ${list.sort_order || "desc"}`)
		}
		return null
	}

	async function getFirstValue(doctype: string, field: string, filters = {}, order_by?: string) {
		const [record] = await call("frappe.client.get_list", { doctype, fields: [field], filters, order_by, limit_page_length: 1 })
		return record?.[field] ?? null
	}

	function setRouteVariable(name: string, value: string) {
		if (!activePage.value) return
		routeVariables.value[name] = value
		localStorage.setItem(`${activePage.value.name}:routeVariables`, JSON.stringify(routeVariables.value))
		resetState()
	}

	const resetState = useDebounceFn(async () => {
		const page = activePage.value
		if (!page) return
		// re-resolve data sources with the new value, then re-run the page script so bindings that
		// derive from a resource (e.g. refs seeded from note.doc via a watcher) re-bind to the new doc.
		await pageScope.setPageResources(page, true)
		await pageScope.setPageScript(page, Boolean(page.is_standard))
	}, 300)

	const codeStore = useCodeStore()
	const pageScope = usePageScope()
	codeStore.setRouteObject(routeObject)
	codeStore.setRouterObject(readonly(router))

	// A page script (or a composable/util it imports) hot-updated. Re-run it in place when it's the
	// active page so new refs/functions and changed dependency code show up on the canvas, in the
	// value selectors and in completions — no reload. Non-active pages refresh lazily on navigation
	// (studioPageScripts caches the latest setup).
	async function setPageData(page: StudioPage) {
		await pageScope.setPageVariables(page)
		await pageScope.setPageResources(page, true)
	}

	const variableConfigs = computed<Record<string, Variable>>(() => {
		const configs: Record<string, Variable> = {}
		studioVariables.data.map((variable: Variable) => {
			configs[variable.variable_name] = {
				...variable,
				initial_value: getInitialVariableValue(variable),
			}
		})
		return configs
	})

	const variableOptions = computed(() => {
		const options: VariableOption[] = []

		function traverse(obj: any, path = "") {
			for (const key in obj) {
				const currentPath = path ? `${path}.${key}` : key
				const variableType = path === "" ? variableConfigs.value[key]?.variable_type : typeof obj[key]
				options.push({
					value: currentPath,
					label: currentPath,
					type: variableType,
				})

				if (typeof obj[key] === "object" && obj[key] !== null) {
					// add nested properties
					traverse(obj[key], currentPath)
				}
			}
		}

		traverse(pageScope.variables)
		return options
	})

	const pageScriptBindingOptions = computed<VariableOption[]>(() => {
		return Object.entries(pageScope.pageScriptTemplateBindings).map(([key, value]) => ({
			value: key,
			label: key,
			type: typeof value,
		}))
	})

	return {
		// studio app
		activeApp,
		setApp,
		deleteApp,
		updateActiveApp,
		appPages,
		setAppPages,
		getAppPageRoute,
		createPage,
		// custom components
		setCustomComponents,
		loadCustomVueComponents,
		customVueComponents,
		// studio pages
		pageBlocks,
		selectedPage,
		settingPage,
		savingPage,
		publishingApp,
		pageConflict,
		activePage,
		setPage,
		savePage,
		updateActivePage,
		updatePage,
		pageAllowsGuests,
		syncPageModified,
		refreshActivePageModified,
		reloadActivePageScript,
		reloadActiveAppRouterScript,
		publishApp,
		unpublishApp,
		openPage,
		routeObject,
		routeVariables,
		areRouteVariablesSet,
		setRouteVariable,
		// data/code
		variableConfigs,
		setPageData,
		variableOptions,
		pageScriptBindingOptions,
	}
})

export default useStudioStore
