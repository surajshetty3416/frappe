import frappeUIPreset from "frappe-ui/tailwind"

/** @type {import('tailwindcss').Config} */
export default {
	presets: [frappeUIPreset],
	content: { relative: true, files: ["./src/**/*.{vue,ts}"] },
}
