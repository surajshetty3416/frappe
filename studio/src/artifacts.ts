import { call } from "frappe-ui"

// An artifact is a record a layer edits in Studio: a web page, a workbook, an app.
export interface Artifact {
	doctype: string
	name: string
	label: string
	title: string
	route: string
}

export interface Chat {
	name: string
	title: string
	modified: string
	artifacts: Artifact[]
}

export const getHistory = (limit = 30): Promise<Chat[]> => call("frappe.ai.artifacts.get_history", { limit })

export const getArtifactSession = (doctype: string, name: string): Promise<Pick<Chat, "name" | "title" | "modified"> | null> =>
	call("frappe.ai.artifacts.get_artifact_session", { reference_doctype: doctype, reference_name: name })

export const getSessionArtifacts = (session: string): Promise<Artifact[]> =>
	call("frappe.ai.artifacts.get_session_artifacts", { session })

export const linkArtifact = (session: string, doctype: string, name: string): Promise<Artifact> =>
	call("frappe.ai.artifacts.link_artifact", { session, reference_doctype: doctype, reference_name: name })

const LAYER_ICONS: Record<string, string> = {
	web: "lucide-globe",
	analytics: "lucide-chart-column",
	ui: "lucide-blocks",
}

export const artifactIcon = (artifact: Artifact) =>
	LAYER_ICONS[artifact.route.split("/")[2]] ?? "lucide-file"
