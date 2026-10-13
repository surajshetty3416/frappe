import { call } from "frappe-ui"
import type { RouteLocationNormalizedLoaded } from "vue-router"

import type { ArtifactEditor } from "./editor"

declare global {
	interface Window {
		studio_artifacts?: Record<string, { label: string; route: string; title_field: string }>
	}
}

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

// A route opens an artifact when one of its records names it in `meta.artifact`; a layer that
// implements the shell's editor contract adds `editor`, and its route renders `editor.preview`.
export interface ArtifactRoute {
	doctype: string
	param: string
	editor?: () => Promise<{ default: ArtifactEditor }>
}

export function routeArtifact(route: RouteLocationNormalizedLoaded) {
	const record = [...route.matched].reverse().find((match) => match.meta.artifact)
	if (!record) return null
	const spec = record.meta.artifact as ArtifactRoute
	const name = String(route.params[spec.param])
	// an editor still creating its record ("new") has no artifact yet
	return name === "new" ? null : { doctype: spec.doctype, name, editor: spec.editor }
}

export const artifactLabel = (doctype: string) => window.studio_artifacts?.[doctype]?.label ?? doctype

export interface ArtifactInfo {
	title: string
	owner: string
	creation: string
	modified: string
}

export async function getArtifactInfo(doctype: string, name: string): Promise<ArtifactInfo> {
	const titleField = window.studio_artifacts?.[doctype]?.title_field ?? "name"
	const doc = await call("frappe.client.get_value", {
		doctype,
		filters: name,
		fieldname: JSON.stringify([titleField, "owner", "creation", "modified"]),
	})
	return { title: doc?.[titleField] || name, owner: doc?.owner, creation: doc?.creation, modified: doc?.modified }
}

export interface Version {
	name: string
	creation: string
	owner: string
	source: "Person" | "Agent"
	label: string
}

export const getVersions = (doctype: string, name: string): Promise<Version[]> =>
	call("frappe.ai.versions.get_versions", { doctype, name })

export const restoreVersion = (version: string) => call("frappe.ai.versions.restore_version", { version })

const LAYER_ICONS: Record<string, string> = {
	data: "lucide-database",
	agents: "lucide-bot",
	web: "lucide-globe",
	analytics: "lucide-chart-column",
	ui: "lucide-blocks",
}

export const artifactIcon = (artifact: Pick<Artifact, "route">) =>
	LAYER_ICONS[artifact.route.split("/")[2]] ?? "lucide-file"
