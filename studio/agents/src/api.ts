import { call } from "frappe-ui"

export type Flag = 0 | 1
export type RunStatus = "Running" | "Waiting" | "Success" | "Partially Failed" | "Failed" | "Skipped"

export interface AgentRow {
	name: string
	title: string
	description: string | null
	model: string
	enabled: Flag
	tools: number
	modified: string
}

export interface AutomationRow {
	name: string
	title: string
	enabled: Flag
	trigger: string
	does: string
	last_run: { status: RunStatus; started_at: string } | null
	modified: string
}

export interface AgentDoc {
	name: string
	title: string
	description?: string
	enabled: Flag
	model: string
	reasoning_effort?: string
	instructions: string
	modified: string
	tools: { tool: string }[]
	skills: { skill: string }[]
	[key: string]: unknown
}

export interface StepCard {
	idx: number
	kind: "Action" | "Wait" | "WaitForEvent" | "If"
	label: string
	action_type?: string
	parent_step?: number
	branch?: "If" | "Else"
	detail?: string
	agent?: string
	agent_title?: string
	prompt?: string
	params?: { label: string; value: string }[]
}

export interface AutomationDoc {
	name: string
	title: string
	enabled: Flag
	document_type?: string
	trigger_type: string
	cron_expression?: string
	next_run?: string
	run_as: string
	automation_user?: string
	stop_on_error: Flag
	modified: string
	[key: string]: unknown
}

export interface Flow {
	doc: AutomationDoc
	trigger: string
	conditions: string[]
	condition: string | null
	steps: StepCard[]
}

export interface RunRow {
	name: string
	status: RunStatus
	started_at: string | null
	ended_at: string | null
	reference_doctype: string | null
	reference_name: string | null
	error_summary: string | null
}

export interface RunStep {
	idx: number
	label: string
	action_type: string
	status: "Success" | "Failed" | "Skipped" | "Waiting"
	duration_ms: number
	detail: string | null
	message: string | null
	agent?: string
	agent_run?: { name: string; status: string; output: string | null; error: string | null; session: string } | null
}

export interface Run extends RunRow {
	steps: RunStep[]
}

export const getHome = (): Promise<{ agents: AgentRow[]; automations: AutomationRow[] }> => call("frappe.agents.api.get_home")

export const getAgent = (name: string): Promise<AgentDoc> => call("frappe.client.get", { doctype: "Flow Agent", name })

export const getFlow = (name: string): Promise<Flow> => call("frappe.agents.api.get_flow", { name })

export const getRuns = (automation: string): Promise<RunRow[]> => call("frappe.agents.api.get_runs", { automation })

export const getRun = (name: string): Promise<Run> => call("frappe.agents.api.get_run", { name })

export const runNow = (automation: string): Promise<{ document: string | null }> =>
	call("frappe.agents.api.run_now", { automation })

export const setValue = (doctype: string, name: string, values: Record<string, unknown>) =>
	call("frappe.client.set_value", { doctype, name, fieldname: values })

export const renameDoc = (doctype: string, name: string, newName: string): Promise<string> =>
	call("frappe.client.rename_doc", { doctype, old_name: name, new_name: newName })

export const errorText = (error: unknown) => {
	const messages = (error as { messages?: string[] })?.messages
	const text = messages?.length ? messages.join(" ") : (error as Error)?.message
	return (text || "That did not work").replace(/<[^>]+>/g, "")
}

const SKIPPED = new Set(["owner", "creation", "modified", "modified_by", "docstatus", "idx", "parent", "parentfield", "parenttype", "doctype"])

// the record as JSON, without the bookkeeping and the empty values
export function docJSON(doc: Record<string, unknown>): string {
	const compact = (value: unknown): unknown => {
		if (Array.isArray(value)) return value.map(compact)
		if (!value || typeof value !== "object") return value
		return Object.fromEntries(
			Object.entries(value)
				.filter(([key, item]) => !SKIPPED.has(key) && !key.startsWith("_") && ![null, "", 0].includes(item as never) && !(Array.isArray(item) && !item.length))
				.filter(([key]) => !(key === "name" && "parent" in (value as object)))
				.map(([key, item]) => [key, compact(item)])
		)
	}
	return JSON.stringify(compact(doc), null, 2)
}

export const STATUS_DOT: Record<string, string> = {
	Success: "bg-surface-green-7",
	Completed: "bg-surface-green-7",
	Running: "bg-surface-blue-7",
	Waiting: "bg-surface-amber-6",
	Paused: "bg-surface-amber-6",
	"Partially Failed": "bg-surface-amber-6",
	Failed: "bg-surface-red-7",
	Denied: "bg-surface-red-7",
	Skipped: "bg-surface-gray-5",
}
