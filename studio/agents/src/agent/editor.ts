// A Flow Agent in Studio's editor shell: a test chat with it as the preview.
import { defineArtifactEditor } from "@shell/editor"
import { findTab } from "@shell/tabs"
import { toast } from "frappe-ui"

import { docJSON, errorText, renameDoc, setValue } from "../api"
import AgentDetails from "./AgentDetails.vue"
import AgentPreview from "./AgentPreview.vue"
import { agent, open, preview } from "./state"

export default defineArtifactEditor({
	preview: AgentPreview,
	// the test chat is the preview, so there is nothing to select
	modes: ["preview"],

	title: () => agent.doc?.title ?? agent.name,
	async rename(title) {
		const old = agent.name
		try {
			const name = await renameDoc("Flow Agent", old, title)
			const path = preview.router?.currentRoute.value.fullPath.replace(encodeURIComponent(old), encodeURIComponent(name)) ?? ""
			const tab = findTab("Flow Agent", old)
			if (tab) Object.assign(tab, { name, title: name, path })
			await preview.router?.replace(path)
		} catch (error) {
			toast.error(errorText(error))
		}
	},
	status() {
		if (!agent.doc) return { label: "Loading…", theme: "gray" }
		return agent.doc.enabled ? { label: "On", theme: "green" } : { label: "Off", theme: "gray" }
	},
	primaryAction() {
		if (!agent.doc || agent.doc.enabled) return null
		return {
			label: "Enable",
			icon: "lucide-power",
			run: async () => {
				await setValue("Flow Agent", agent.name, { enabled: 1 })
				await open(agent.name)
			},
		}
	},
	detailsForm: () => (agent.doc ? { component: AgentDetails } : null),
	details() {
		const doc = agent.doc
		if (!doc) return []
		const effort = doc.reasoning_effort
		return [
			{ label: "Model", value: doc.model },
			{ label: "Reasoning", value: effort ? effort.charAt(0).toUpperCase() + effort.slice(1) : "Model default" },
			{ label: "Skills", value: doc.skills.map((row) => row.skill).join(", ") || "None" },
		]
	},
	code: () => ({ language: "json", content: agent.doc ? docJSON(agent.doc) : "" }),
	async reload() {
		if (agent.name) await open(agent.name)
	},

	elementAt: () => null,
	elementRect: () => null,
	textNode: () => null,
	setText: () => {},
	properties: () => [],
})
