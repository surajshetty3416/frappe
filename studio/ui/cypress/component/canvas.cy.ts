import { pinia } from "../support/component"

import { h } from "vue"
import { createMemoryHistory, createRouter } from "vue-router"
import { setActivePinia } from "pinia"
// @ts-ignore
import { resourcesPlugin } from "frappe-ui"

import StudioCanvas from "@ui/components/StudioCanvas.vue"
import Block from "@ui/utils/block"
import { COMPONENTS } from "@ui/data/components"
import { getBlockInstance } from "@ui/utils/serializer"
import getBlockTemplate from "@ui/utils/blockTemplate"
import { registerGlobalComponents } from "@ui/globals"

const canvasElement = () => document.querySelector(".canvas") as HTMLElement

// the editor navigates on the shell's router; the guard only needs one to cancel on
const router = createRouter({
	history: createMemoryHistory(),
	routes: [
		{ path: "/app/test/page", name: "TestPage", component: { render: () => h("div") } },
		{ path: "/home", name: "Home", component: { render: () => h("div") } },
	],
})

describe("canvas navigation guard", () => {
	beforeEach(() => {
		cy.wrap(router.push("/app/test/page"))

		Block.setComponents(COMPONENTS)
		setActivePinia(pinia)
		cy.mount(StudioCanvas as any, {
			props: { componentTree: getBlockInstance({ ...getBlockTemplate("body") }) },
			global: { plugins: [pinia, router, resourcesPlugin, { install: registerGlobalComponents }] },
		})
		cy.get(".canvas").should("exist")
	})

	it("cancels navigation triggered by a click inside the canvas", () => {
		cy.then(() => {
			canvasElement().dispatchEvent(new MouseEvent("mousedown", { bubbles: true }))
			canvasElement().dispatchEvent(new MouseEvent("mouseup", { bubbles: true }))
			return router.push({ name: "Home" })
		})
		cy.wrap(null).should(() => expect(router.currentRoute.value.name).to.eq("TestPage"))
	})

	it("allows navigation after a press in the canvas is released outside it", () => {
		cy.then(() => {
			canvasElement().dispatchEvent(new MouseEvent("mousedown", { bubbles: true, button: 2 }))
			document.body.dispatchEvent(new MouseEvent("mouseup", { bubbles: true, button: 2 }))
		})
		cy.wait(10)
		cy.then(() => router.push({ name: "Home" }))
		cy.wrap(null).should(() => expect(router.currentRoute.value.name).to.eq("Home"))
	})
})
