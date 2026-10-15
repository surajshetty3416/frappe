import { useDebounceFn, useStorage } from "@vueuse/core"
import { call } from "frappe-ui"
import { ref } from "vue"
import type { RouteLocationNormalizedLoaded, RouteLocationRaw } from "vue-router"

import type { Artifact } from "./artifacts"
import { chats } from "./chats"
import { onListUpdate } from "./realtime"

// A project gathers one piece of work: its chats, what they made, and the skills its chats use.
export interface Project {
	name: string
	title: string
	description: string | null
	modified: string
}

export interface ProjectDoc extends Project {
	can_write: boolean
}

export interface Skill {
	name: string
	title: string
	description: string | null
	enabled: 0 | 1
	is_global: 0 | 1
	// the project's own; the others are global, in every chat
	own: boolean
	// what a person types after /skill:, for a skill they may start
	command: string | null
}

export interface RunningChat {
	name: string
	title: string
	modified: string
	status: "Running" | "Paused"
	// an orchestrator's routed tasks that ended, of all of them
	tasks: { done: number; total: number } | null
}

export type ProjectArtifact = Artifact & { modified: string; project?: { name: string; title: string } | null }

export interface ProjectPage {
	project: ProjectDoc
	artifacts: ProjectArtifact[]
	skills: Skill[]
}

export const projects = ref<Project[]>([])
export const projectsLoaded = ref(false)
// the project on screen: the open project, or the project of the open chat
export const activeProject = ref<string | null>(null)
// the project the person last worked in, where a chat started with no other project goes
export const lastProject = useStorage<string | null>("studio-project", null)

export async function loadProjects() {
	projects.value = await call<Project[]>("frappe.ai.projects.get_projects")
	projectsLoaded.value = true
	if (lastProject.value && !projects.value.some((project) => project.name === lastProject.value)) lastProject.value = null
}

let watching = false
export function watchProjects() {
	if (watching) return
	watching = true
	loadProjects()
	onListUpdate("Studio Project", useDebounceFn(loadProjects, 400))
}

export const projectTitle = (name: string | null) => projects.value.find((project) => project.name === name)?.title ?? ""

// the project a route belongs to, by its own param, its chat, or the last one worked in
export function routeProject(route: RouteLocationNormalizedLoaded): string | null {
	if (typeof route.params.project === "string") return route.params.project
	if (typeof route.query.project === "string") return route.query.project
	const session = route.name === "studio-chat" ? route.params.session : route.query.chat
	const chat = typeof session === "string" ? chats.value.find((open) => open.name === session) : null
	return chat?.project ?? lastProject.value
}

export const projectRoute = (project: string, tab?: string): RouteLocationRaw => ({
	name: "studio-project",
	params: { project, tab: tab ?? "" },
})

// the home is a new chat, in the project it names or the last one worked in
export const newChatRoute = (project: string | null, prompt?: string): RouteLocationRaw => ({
	name: "studio-home",
	query: { ...(project ? { project } : {}), ...(prompt ? { prompt } : {}) },
})

export const getProject = (project: string) => call<ProjectPage>("frappe.ai.projects.get_project", { project })

// the open project's page, which its heading and the lists under its chatbox share
export const projectPage = ref<ProjectPage | null>(null)
export const projectPageFailed = ref(false)
export async function loadProjectPage(project: string) {
	try {
		const page = await getProject(project)
		if (project === activeProject.value) projectPage.value = page
	} catch {
		if (project === activeProject.value) projectPageFailed.value = true
	}
}

export const getRunningChats = (project: string) => call<RunningChat[]>("frappe.ai.projects.get_running_chats", { project })

// every artifact of `doctypes`, or only what `project` made
export const getArtifacts = (doctypes: string[], project: string | null) =>
	call<ProjectArtifact[]>("frappe.ai.projects.get_artifacts", { doctypes, project })

export async function createProject(title: string, description: string) {
	const doc = await call<{ name: string }>("frappe.client.insert", {
		doc: { doctype: "Studio Project", title, description },
	})
	await loadProjects()
	return doc.name
}

export const setProjectSkills = (project: string, skills: string[]) =>
	updateProject(project, { skills: skills.map((skill) => ({ skill })) })

// the project and its chats; what they made stays
export async function deleteProject(project: string) {
	await call("frappe.client.delete", { doctype: "Studio Project", name: project })
	await loadProjects()
}

export async function updateProject(project: string, values: Record<string, unknown>) {
	await call("frappe.client.set_value", { doctype: "Studio Project", name: project, fieldname: values })
	if ("title" in values || "description" in values) await loadProjects()
}

export const errorText = (error: unknown) => {
	const messages = (error as { messages?: string[] })?.messages
	const text = messages?.length ? messages.join(" ") : (error as Error)?.message
	return (text || "That did not work").replace(/<[^>]+>/g, "")
}
