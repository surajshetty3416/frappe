// The open agent: what its preview and the shell's editor contract both read.
import { reactive } from "vue"
import type { Router } from "vue-router"

import { type AgentDoc, errorText, getAgent } from "../api"

export const agent = reactive({ name: "", doc: null as AgentDoc | null, error: "" })

export const preview: { router: Router | null } = { router: null }

export async function open(name: string) {
	agent.name = name
	agent.error = ""
	try {
		const doc = await getAgent(name)
		if (agent.name === name) agent.doc = doc
	} catch (error) {
		if (agent.name !== name) return
		agent.doc = null
		agent.error = errorText(error)
	}
}
