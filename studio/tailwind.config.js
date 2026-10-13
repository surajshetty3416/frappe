import frappeUIPreset, { content as frappeUIContent } from "frappe-ui/tailwind"

// The shell's own classes, plus Tailwind's base for every layer. Each layer compiles its
// components and utilities from its own config (see the `@config` at the top of its CSS).
// The shell draws what layers name, such as icons on its toolbar, and mounts their components,
// so it scans every layer's source too.
export default {
	presets: [frappeUIPreset],
	content: [
		"./index.html",
		"./src/**/*.{vue,js,ts}",
		"./{agents,ai,data,settings,ui,web}/src/**/*.{vue,js,ts}",
		"./analytics/src2/**/*.{vue,js,ts}",
		// the chat's menu sits in the shell's top bar, its items portaled to the page
		"../harness/ui/core/src/components/ChatMenu.vue",
		...frappeUIContent,
	],
}
