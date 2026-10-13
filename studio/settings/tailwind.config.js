import frappeUIPreset from "frappe-ui/tailwind"

// the frappe-ui settings parts lay out with breakpoint classes nothing else in Studio compiles
export default {
	presets: [frappeUIPreset],
	content: {
		relative: true,
		files: ["./src/**/*.{vue,ts}", "../node_modules/frappe-ui/src/components/SettingsDialog/*.vue"],
	},
}
