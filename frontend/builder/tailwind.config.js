import containerQueries from "@tailwindcss/container-queries";
import typography from "@tailwindcss/typography";
import colors from "tailwindcss/colors";
import frappeUIPreset, { content as frappeUIContent } from "frappe-ui/tailwind";
import plugin from "tailwindcss/plugin";

export default {
	presets: [frappeUIPreset],
	content: {
		relative: true,
		files: [
			"./src/**/*.{vue,js,ts,jsx,tsx}",
			// tracks the library's own source dirs, including the experimental subpath
			...frappeUIContent,
			// @framework/ui ships raw source too, compiled by this app's bundler
			"../../ui/src/**/*.{vue,js,ts,jsx,tsx}",
		],
	},
	plugins: [
		plugin(function ({ matchUtilities, theme }) {
			matchUtilities(
				{
					"auto-fill": (value) => ({
						gridTemplateColumns: `repeat(auto-fill, minmax(min(${value}, 100%), 1fr))`,
					}),
					"auto-fit": (value) => ({
						gridTemplateColumns: `repeat(auto-fit, minmax(min(${value}, 100%), 1fr))`,
					}),
				},
				{
					values: theme("width", {}),
				},
			);
		}),
		containerQueries,
		typography,
	],
	theme: {
		extend: {
			transitionProperty: {
				size: "transform, border-radius",
			},
			colors: {
				zinc: colors.zinc,
			},
		},
	},
};
