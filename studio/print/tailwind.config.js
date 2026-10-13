import frappeUIPreset from "frappe-ui/tailwind"

/** @type {import('tailwindcss').Config} */
export default {
	presets: [frappeUIPreset],
	// the preview it shares with the other outputs of the HTML canvas lives with the web layer
	content: { relative: true, files: ["./src/**/*.{vue,ts}", "../web/src/output/**/*.{vue,ts}"] },
}
