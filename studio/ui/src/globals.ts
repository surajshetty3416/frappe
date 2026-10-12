import { App, Component, defineAsyncComponent, shallowRef } from "vue"
import {
	Alert,
	Avatar,
	Badge,
	Breadcrumbs,
	Button,
	Checkbox,
	Combobox,
	DatePicker,
	TimePicker,
	DateTimePicker,
	DateRangePicker,
	Dialog,
	Divider,
	Dropdown,
	ErrorMessage,
	FileUploader,
	FormControl,
	FormLabel,
	Icon,
	LoadingIndicator,
	LoadingText,
	MultiSelect,
	Password,
	Progress,
	Popover,
	Radio,
	RadioGroup,
	Rating,
	Select,
	Sidebar,
	SidebarHeader,
	SidebarItem,
	SidebarLabel,
	SidebarCollapseToggle,
	SidebarCard,
	SidebarRail,
	SidebarRailItem,
	Slider,
	Switch,
	TabButtons,
	Tabs,
	TextInput,
	Textarea,
	Tooltip,
	Tree,
	ContextMenu,
	Duration,
	Spinner,
	SettingsDialog,
	SettingsSidebar,
	SettingsNavGroup,
	SettingsNavItem,
	SettingsContent,
	SettingsPanel,
	SettingsHeader,
	SettingsBody,
	SettingsRow,
} from "frappe-ui"
import {
	Calendar,
	CommandPalette,
	CommandPaletteItem,
	ListView,
	TextEditor,
} from "frappe-ui/experimental"
import {
	AreaChart,
	BarChart,
	LineChart,
	DonutChart,
	FunnelChart,
	HeatmapChart,
	ScatterChart,
	SankeyChart,
	NumberCard,
} from "frappe-ui/charts"
import {
	List,
	ListRows,
	ListRow,
	ListCell,
	ListHeader,
	ListHeaderCell,
	ListHeaderCellSort,
	ListGroup,
} from "frappe-ui/list"

import Container from "@ui/components/AppLayout/Container.vue"
import FitContainer from "@ui/components/AppLayout/FitContainer.vue"
import SplitView from "@ui/components/AppLayout/SplitView.vue"
import Repeater from "@ui/components/AppLayout/Repeater.vue"
import HTML from "@ui/components/AppLayout/HTML.vue"
import CardList from "@ui/components/AppLayout/CardList.vue"
import AvatarCard from "@ui/components/AppLayout/AvatarCard.vue"
import Audio from "@ui/components/AppLayout/Audio.vue"
import ImageView from "@ui/components/AppLayout/ImageView.vue"
import TextBlock from "@ui/components/AppLayout/TextBlock.vue"
import AppHeader from "@ui/components/AppLayout/AppHeader.vue"
import BottomTabs from "@ui/components/AppLayout/BottomTabs.vue"
import MarkdownEditor from "@ui/components/AppLayout/MarkdownEditor.vue"

import { vueComponents } from "@ui/data/vueComponents"
import { CustomVueComponentMeta } from "@ui/types/vue"

export function registerGlobalComponents(app: App) {
	// the editor shares the app with other layers, which register some of the same frappe-ui components
	const register = (name: string, component: Component) => app.component(name) || app.component(name, component)

	register("Alert", Alert)
	register("Avatar", Avatar)
	register("Badge", Badge)
	register("Breadcrumbs", Breadcrumbs)
	register("Button", Button)
	register("Checkbox", Checkbox)
	register("Combobox", Combobox)
	register("DatePicker", DatePicker)
	register("TimePicker", TimePicker)
	register("DateTimePicker", DateTimePicker)
	register("DateRangePicker", DateRangePicker)
	register("Dialog", Dialog)
	register("Divider", Divider)
	register("Dropdown", Dropdown)
	register("ErrorMessage", ErrorMessage)
	register("FileUploader", FileUploader)
	register("FormControl", FormControl)
	register("FormLabel", FormLabel)
	register("Icon", Icon)
	register("LoadingIndicator", LoadingIndicator)
	register("LoadingText", LoadingText)
	register("MultiSelect", MultiSelect)
	register("Password", Password)
	register("Progress", Progress)
	register("Popover", Popover)
	register("Rating", Rating)
	register("Select", Select)
	register("Slider", Slider)
	register("Switch", Switch)
	register("TabButtons", TabButtons)
	register("Tabs", Tabs)
	register("TextInput", TextInput)
	register("Textarea", Textarea)
	register("Tooltip", Tooltip)
	register("Tree", Tree)
	register("ListView", ListView)
	register("TextEditor", TextEditor)
	register("CommandPalette", CommandPalette)
	register("CommandPaletteItem", CommandPaletteItem)
	register("Calendar", Calendar)
	register("ContextMenu", ContextMenu)
	register("Duration", Duration)
	register("Spinner", Spinner)

	// frappe-ui/charts
	register("AreaChart", AreaChart)
	register("BarChart", BarChart)
	register("LineChart", LineChart)
	register("DonutChart", DonutChart)
	register("FunnelChart", FunnelChart)
	register("HeatmapChart", HeatmapChart)
	register("ScatterChart", ScatterChart)
	register("SankeyChart", SankeyChart)
	register("NumberCard", NumberCard)

	// List family (frappe-ui/list) — dropped as a tree via the `list` block template.
	register("List", List)
	register("ListRows", ListRows)
	register("ListRow", ListRow)
	register("ListCell", ListCell)
	register("ListHeader", ListHeader)
	register("ListHeaderCell", ListHeaderCell)
	register("ListHeaderCellSort", ListHeaderCellSort)
	register("ListGroup", ListGroup)

	// SettingsDialog family — dropped as a tree via the `settings-dialog` block template.
	register("SettingsDialog", SettingsDialog)
	register("SettingsSidebar", SettingsSidebar)
	register("SettingsNavGroup", SettingsNavGroup)
	register("SettingsNavItem", SettingsNavItem)
	register("SettingsContent", SettingsContent)
	register("SettingsPanel", SettingsPanel)
	register("SettingsHeader", SettingsHeader)
	register("SettingsBody", SettingsBody)
	register("SettingsRow", SettingsRow)

	// Sidebar family — dropped as a tree via the `sidebar` block template.
	register("Sidebar", Sidebar)
	register("SidebarHeader", SidebarHeader)
	register("SidebarItem", SidebarItem)
	register("SidebarLabel", SidebarLabel)
	register("SidebarCollapseToggle", SidebarCollapseToggle)
	register("SidebarCard", SidebarCard)

	// SidebarRail family — dropped as a tree via the `sidebar-rail` block template.
	register("SidebarRail", SidebarRail)
	register("SidebarRailItem", SidebarRailItem)

	// RadioGroup family — dropped as a tree via the `radio-group` block template.
	register("RadioGroup", RadioGroup)
	register("Radio", Radio)

	// @framework/ui components
	register(
		"FormLayout",
		defineAsyncComponent(() => import("@framework/ui/components/FormLayout/FormLayout.vue")),
	)
	register(
		"Link",
		defineAsyncComponent(() => import("@framework/ui/components/Link/Link.vue")),
	)
	register(
		"Grid",
		defineAsyncComponent(() => import("@framework/ui/components/Grid/Grid.vue")),
	)
	register(
		"Phone",
		defineAsyncComponent(() => import("@framework/ui/components/Phone/Phone.vue")),
	)
	register(
		"TableMultiSelect",
		defineAsyncComponent(() => import("@framework/ui/components/TableMultiSelect/TableMultiSelect.vue")),
	)
	register(
		"NotificationPanel",
		defineAsyncComponent(() => import("@framework/ui/components/Notifications/NotificationPanel.vue")),
	)
	register(
		"NotificationItem",
		defineAsyncComponent(() => import("@framework/ui/components/Notifications/NotificationItem.vue")),
	)
	register(
		"ActivityTimeline",
		defineAsyncComponent(() => import("@framework/ui/components/ActivityTimeline/ActivityTimeline.vue")),
	)
	register(
		"EmailItem",
		defineAsyncComponent(() => import("@framework/ui/components/ActivityTimeline/EmailItem.vue")),
	)
	register(
		"CommentItem",
		defineAsyncComponent(() => import("@framework/ui/components/ActivityTimeline/CommentItem.vue")),
	)
	register(
		"EmailComposer",
		defineAsyncComponent(() => import("@framework/ui/components/Composer/EmailComposer/EmailComposer.vue")),
	)
	register(
		"CommentComposer",
		defineAsyncComponent(
			() => import("@framework/ui/components/Composer/CommentComposer/CommentComposer.vue"),
		),
	)
	register(
		"Filter",
		defineAsyncComponent(() => import("@framework/ui/components/Filter/Filter.vue")),
	)
	register(
		"SortBy",
		defineAsyncComponent(() => import("@framework/ui/components/SortBy/SortBy.vue")),
	)
	register(
		"QuickFilter",
		defineAsyncComponent(() => import("@framework/ui/components/QuickFilter/QuickFilter.vue")),
	)
	register(
		"ColumnSettings",
		defineAsyncComponent(() => import("@framework/ui/components/ColumnSettings/ColumnSettings.vue")),
	)
	register(
		"ListViewShell",
		defineAsyncComponent(() => import("@framework/ui/components/ListView/ListViewShell.vue")),
	)
	register(
		"FileUploadDialog",
		defineAsyncComponent(() => import("@framework/ui/components/FileUpload/FileUploadDialog.vue")),
	)
	register(
		"AttachmentsList",
		defineAsyncComponent(() => import("@framework/ui/components/FileUpload/AttachmentsList.vue")),
	)
	register(
		"UploadTray",
		defineAsyncComponent(() => import("@framework/ui/components/FileUpload/UploadTray.vue")),
	)

	// studio components
	register("Container", Container)
	register("FitContainer", FitContainer)
	register("SplitView", SplitView)
	register("Repeater", Repeater)
	register("HTML", HTML)
	register("CardList", CardList)
	register("AvatarCard", AvatarCard)
	register("Audio", Audio)
	register("ImageView", ImageView)
	register("TextBlock", TextBlock)
	register("AppHeader", AppHeader)
	register("BottomTabs", BottomTabs)
	register("MarkdownEditor", MarkdownEditor)
}

export const customVueComponentsRegistry = shallowRef<Record<string, any>>({})
/**
 * Dynamically register custom Vue components from a specific Frappe app into the custom components registry.
 * @param frappeApp - The Frappe app name to fetch components from
 */
export async function registerCustomVueComponents(frappeApp: string): Promise<CustomVueComponentMeta[]> {
	try {
		if (!frappeApp) return []
		const components: CustomVueComponentMeta[] = await vueComponents.reload({ frappe_app: frappeApp })

		const registry = { ...customVueComponentsRegistry.value }
		for (const comp of components) {
			try {
				const asyncComp = defineAsyncComponent(() => import(/* @vite-ignore */ comp.file_path))
				registry[comp.component_name] = asyncComp
				if (window.__APP_COMPONENTS__) {
					window.__APP_COMPONENTS__[comp.component_name] = asyncComp
				}
			} catch (err) {
				console.error(`Failed to load custom component ${comp.component_name}:`, err)
			}
		}
		customVueComponentsRegistry.value = registry
		return components
	} catch (err) {
		console.error("Failed to fetch custom Vue components:", err)
		return []
	}
}

/**
 * Unregister previously registered custom Vue components from the custom components registry.
 * Called when switching apps to clean up components from the previous app's frappe_app.
 */
export function unregisterCustomVueComponents(components: CustomVueComponentMeta[]) {
	const registry = { ...customVueComponentsRegistry.value }
	for (const comp of components) {
		delete registry[comp.component_name]
		if (window.__APP_COMPONENTS__) {
			delete window.__APP_COMPONENTS__[comp.component_name]
		}
	}
	customVueComponentsRegistry.value = registry
}

// Re-sync the registry to the app's current custom components. register() only merges, so on its
// own a removed component would linger; this also evicts any that no longer exist. Pass an empty
// frappeApp to clear them all (e.g. a non-standard app). Shared by the editor and the preview.
export async function reloadCustomVueComponents(frappeApp: string): Promise<CustomVueComponentMeta[]> {
	const before = Object.keys(customVueComponentsRegistry.value)
	const components = await registerCustomVueComponents(frappeApp)

	const current = new Set(components.map((comp) => comp.component_name))
	const removed = before.filter((name) => !current.has(name)).map((name) => ({ component_name: name }))
	if (removed.length) unregisterCustomVueComponents(removed as CustomVueComponentMeta[])

	return components
}
