import path from "node:path"

import frameworkUI from "@framework/ui/vite"
import vue from "@vitejs/plugin-vue"
import vueJsx from "@vitejs/plugin-vue-jsx"
import frappeui from "frappe-ui/vite"
import { defineConfig } from "vite"

import hostDependencies from "./build/hostDependencies.js"

const here = (...parts) => path.resolve(import.meta.dirname, ...parts)
const flowCore = here("../harness/ui/core")

export default defineConfig({
	plugins: [
		frappeui({
			frappeProxy: {
				// VITE_PORT runs a second dev server beside the default one (webserver port + 80)
				port: Number(process.env.VITE_PORT) || undefined,
				source: "^/(desk|app|login|logout|api|assets|files|private|builder_assets|pages)",
			},
			lucideIcons: true,
			jinjaBootData: true,
			// the layers bring their own @codemirror/lang-* packages
			codeLanguages: false,
			buildConfig: {
				outDir: here("../frappe/public/frontend"),
				indexHtmlPath: here("../frappe/www/_frontend.html"),
				baseUrl: "/assets/frappe/frontend/",
			},
		}),
		vue(),
		vueJsx(),
		frameworkUI({ dedupe: ["pinia", "@vueuse/core", "echarts", "zrender"] }),
		hostDependencies([flowCore]),
	],
	resolve: {
		alias: [
			{ find: /^@shell\//, replacement: here("src") + "/" },
			{ find: /^@builder\//, replacement: here("builder/src") + "/" },
			{ find: /^@insights\//, replacement: here("insights/src2") + "/" },
			{ find: /^@studio\//, replacement: here("studio/src") + "/" },
			{ find: /^@flow\/(?!ui-core)/, replacement: here("flow/src") + "/" },
			// @flow/ui-core imports single components from frappe-ui's source, which the
			// package's exports map does not list
			{ find: /^frappe-ui\/src\//, replacement: here("node_modules/frappe-ui/src") + "/" },
		],
		dedupe: [
			"prosemirror-model",
			"prosemirror-view",
			"prosemirror-state",
			"prosemirror-transform",
			"@codemirror/state",
			"@codemirror/view",
			"@codemirror/language",
			"@lezer/common",
			"@lezer/highlight",
			"@lezer/lr",
		],
	},
	define: {
		__VUE_PROD_HYDRATION_MISMATCH_DETAILS__: false,
	},
	server: {
		allowedHosts: true,
		fs: { allow: [here("."), here("../ui"), flowCore] },
	},
	build: {
		target: "es2020",
		chunkSizeWarningLimit: 2000,
	},
	optimizeDeps: {
		include: ["engine.io-client", "highlight.js/lib/core"],
		exclude: ["@flow/ui-core"],
	},
})
