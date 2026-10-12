import type { App, Component } from "vue"
import type { NavigationGuardWithThis, RouteRecordRaw } from "vue-router"

export type LayerName = "flow" | "builder" | "insights" | "studio"

// What a layer hands the shell. The shell mounts `component` at `path`, with `routes` as
// its children, and calls `setup` once, the first time someone opens the layer.
export interface Layer {
	name: LayerName
	title: string
	icon: string
	path: string
	component: () => Promise<Component | { default: Component }>
	routes: RouteRecordRaw[]
	setup?: (app: App) => void | Promise<void>
	beforeEnter?: NavigationGuardWithThis<undefined>
}

export const defineLayer = (layer: Layer) => layer
