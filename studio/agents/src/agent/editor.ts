// A Flow Agent in Studio's editor shell: a test chat with it as the preview.
import { defineArtifactEditor } from "@shell/editor"
import { findTab } from "@shell/tabs"
import { toast } from "frappe-ui"

import { docJSON, errorText, renameDoc, setValue } from "../api"
import AgentPreview from "./AgentPreview.vue"
import { agent, open, preview } from "./state"

const list = (values: string[]) => values.join(", ") || "None"

export default defineArtifactEditor({
	preview: AgentPreview,

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
		return agent.doc.enabled ? { label: "Enabled", theme: "green" } : { label: "Disabled", theme: "gray" }
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
	details() {
		const doc = agent.doc
		if (!doc) return []
		return [
			{ label: "Enabled", value: doc.enabled ? "Yes" : "No" },
			{ label: "Model", value: doc.model },
			{ label: "Reasoning effort", value: doc.reasoning_effort || "Model default" },
			{ label: "Tools", value: list(doc.tools.map((row) => row.tool)) },
			{ label: "Skills", value: list(doc.skills.map((row) => row.skill)) },
			{ label: "Description", value: doc.description || "None" },
			{ label: "Instructions", value: doc.instructions },
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
