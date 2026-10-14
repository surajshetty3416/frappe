import { App, Component, defineAsyncComponent } from "vue"
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
import { FRAPPE_UI_CHARTS } from "@ui/utils/constants"
import {
	List,
	ListRow,
	ListCell,
	ListHeader,
	ListHeaderCell,
	ListHeaderCellSort,
	ListGroup,
} from "frappe-ui/list"

import Container from "@ui/components/AppLayout/Container.vue"
import Repeater from "@ui/components/AppLayout/Repeater.vue"
import ListRows from "@ui/components/AppLayout/ListRows.vue"
import HTML from "@ui/components/AppLayout/HTML.vue"
import ImageView from "@ui/components/AppLayout/ImageView.vue"
import TextBlock from "@ui/components/AppLayout/TextBlock.vue"

export function registerGlobalComponents(app: App) {
	const register = (name: string, component: Component) => app.component(name, component)

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

	for (const chart of FRAPPE_UI_CHARTS) {
		register(chart, defineAsyncComponent(() => import("frappe-ui/charts").then((charts) => charts[chart])))
	}

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
	register("Repeater", Repeater)
	register("HTML", HTML)
	register("ImageView", ImageView)
	register("TextBlock", TextBlock)
}
