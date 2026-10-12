import frappeUIPreset, { content as frappeUIContent } from "frappe-ui/tailwind"

// The shell's own classes, plus Tailwind's base for every layer. Each layer compiles its
// components and utilities from its own config (see the `@config` at the top of its CSS).
export default {
	presets: [frappeUIPreset],
	content: ["./index.html", "./src/**/*.{vue,js,ts}", "./*/src/layer.ts", "./analytics/src2/layer.ts", ...frappeUIContent],
}
