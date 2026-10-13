// The open automation: what its preview and the shell's editor contract both read.
import { toast } from "frappe-ui"
import { reactive } from "vue"
import type { Router } from "vue-router"

import { type Flow, errorText, getFlow, runNow } from "../api"

// `choosing`: Run now asks which record to run on
export const automation = reactive({ name: "", flow: null as Flow | null, error: "", choosing: false })

export const preview: { router: Router | null } = { router: null }

export async function open(name: string) {
	automation.name = name
	automation.error = ""
	try {
		const flow = await getFlow(name)
		if (automation.name === name) automation.flow = flow
	} catch (error) {
		if (automation.name !== name) return
		automation.flow = null
		automation.error = errorText(error)
	}
}

export type View = "flow" | "runs"

export const currentView = (): View => (preview.router?.currentRoute.value.query.view === "runs" ? "runs" : "flow")

export function showView(view: View) {
	const route = preview.router?.currentRoute.value
	if (route) preview.router?.replace({ query: { ...route.query, view } })
}

export function startRun() {
	if (automation.flow?.doc.document_type) automation.choosing = true
	else run()
}

export async function run(docname?: string) {
	try {
		const { title } = await runNow(automation.name, docname)
		toast.success(title ? `Running on ${title}` : "Running")
		automation.choosing = false
		showView("runs")
	} catch (error) {
		toast.error(errorText(error))
	}
}
