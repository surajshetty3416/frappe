import frappeUIPreset from "frappe-ui/tailwind";

/** @type {import('tailwindcss').Config} */
export default {
	presets: [frappeUIPreset],
	// Tailwind v3 ignores `content` in presets; frappe-ui and the shared core are
	// compiled by this app, so their globs live here.
	content: {
		relative: true,
		files: [
			"./src/**/*.{vue,js}",
			"../../harness/ui/core/src/**/*.{vue,js}",
			"../node_modules/frappe-ui/src/components/**/*.{vue,js,ts}",
			"../node_modules/frappe-ui/src/utils/**/*.ts",
		],
	},
};
