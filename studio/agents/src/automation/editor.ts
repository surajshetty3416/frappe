// An Automation Flow in Studio's editor shell: the flow drawn top to bottom, and its runs.
import { defineArtifactEditor } from "@shell/editor"
import { toast } from "frappe-ui"

import { docJSON, errorText, setValue } from "../api"
import AutomationPreview from "./AutomationPreview.vue"
import AutomationDetails from "./AutomationDetails.vue"
import { automation, currentView, open, showView, startRun } from "./state"

export default defineArtifactEditor({
	preview: AutomationPreview,
	// the flow is read-only, so there is nothing to select
	modes: ["preview"],
	views: () => [
		{ name: "flow", label: "Flow", active: currentView() === "flow", open: () => showView("flow") },
		{ name: "runs", label: "Runs", active: currentView() === "runs", open: () => showView("runs") },
	],
	detailsForm: () => (automation.flow ? { component: AutomationDetails } : null),

	title: () => automation.flow?.doc.title ?? automation.name,
	async rename(title) {
		try {
			await setValue("Automation Flow", automation.name, { title })
			await open(automation.name)
		} catch (error) {
			toast.error(errorText(error))
		}
	},
	status() {
		if (!automation.flow) return { label: "Loading…", theme: "gray" }
		return automation.flow.doc.enabled ? { label: "On", theme: "green" } : { label: "Off", theme: "gray" }
	},
	primaryAction() {
		if (!automation.flow) return null
		return {
			label: "Run now",
			icon: "lucide-play",
			run: async () => startRun(),
		}
	},
	details() {
		const flow = automation.flow
		if (!flow) return []
		const doc = flow.doc
		return [
			{ label: "Name", value: doc.title },
			{ label: "Trigger", value: flow.trigger },
			{ label: "Trigger type", value: doc.trigger_type },
			...(doc.document_type ? [{ label: "DocType", value: doc.document_type }] : []),
			...(doc.cron_expression ? [{ label: "Cron", value: doc.cron_expression }] : []),
			...(doc.next_run ? [{ label: "Next run", value: doc.next_run }] : []),
			{ label: "Runs as", value: doc.run_as === "Automation User" ? doc.automation_user || "Administrator" : doc.run_as },
			{ label: "On a failed step", value: doc.stop_on_error ? "Stop" : "Go on" },
		]
	},
	code: () => ({ language: "json", content: automation.flow ? docJSON(automation.flow.doc) : "" }),
	async reload() {
		if (automation.name) await open(automation.name)
	},

	elementAt: () => null,
	elementRect: () => null,
	textNode: () => null,
	setText: () => {},
	properties: () => [],
})
