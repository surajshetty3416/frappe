import {
	Avatar,
	Badge,
	Button,
	Combobox,
	Dialog,
	Dropdown,
	ErrorMessage,
	FormControl,
	LoadingIndicator,
	MultiSelect,
	Popover,
	TabButtons,
	Tooltip,
} from 'frappe-ui'
import Toggle from './components/Toggle.vue'

import { App, Component } from 'vue'

const components: Record<string, Component> = {
	Badge,
	Button,
	Dialog,
	Avatar,
	TabButtons,
	Popover,
	Tooltip,
	Toggle,
	Dropdown,
	FormControl,
	LoadingIndicator,
	Combobox,
	MultiSelect,
	ErrorMessage,
}

export function registerGlobalComponents(app: App) {
	for (const [name, component] of Object.entries(components)) {
		// other layers register the same frappe-ui components under these names
		if (!app.component(name)) app.component(name, component)
	}
}
