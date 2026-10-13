// The open automation: what its preview and the shell's editor contract both read.
import { reactive } from "vue"
import type { Router } from "vue-router"

import { type Flow, errorText, getFlow } from "../api"

export const automation = reactive({ name: "", flow: null as Flow | null, error: "" })

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

export const showRuns = () => {
	const route = preview.router?.currentRoute.value
	if (route) preview.router?.replace({ query: { ...route.query, view: "runs" } })
}
