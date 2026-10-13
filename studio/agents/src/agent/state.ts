// The open agent: what its preview and the shell's editor contract both read.
import { call } from "frappe-ui"
import { reactive } from "vue"
import type { Router } from "vue-router"

import { type AgentDoc, errorText, getAgent } from "../api"

export const agent = reactive({ name: "", doc: null as AgentDoc | null, modelId: "", error: "" })

export const preview: { router: Router | null } = { router: null }

export async function open(name: string) {
	agent.name = name
	agent.error = ""
	try {
		const doc = await getAgent(name)
		// the Flow Model's name is its first title, and Settings switches only its model_id
		const model: { model_id?: string } | null = doc.model
			? await call("frappe.client.get_value", { doctype: "Flow Model", filters: doc.model, fieldname: "model_id" })
			: null
		if (agent.name === name) Object.assign(agent, { doc, modelId: model?.model_id ?? doc.model })
	} catch (error) {
		if (agent.name !== name) return
		agent.doc = null
		agent.error = errorText(error)
	}
}
