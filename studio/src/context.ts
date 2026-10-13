import { ref, shallowRef } from "vue"

import { artifactIcon } from "./artifacts"
import type { ArtifactEditor, PreviewElement } from "./editor"

// What the agent is told about the editor beside the chat: the open artifact, the selected
// element and the comments pinned on the preview. FrappeClient.run sends it with each message.

export interface ElementContext {
	id: string
	label: string
	text?: string
}

export interface Comment {
	key: number
	// `doctype/name` of the artifact it is pinned on
	artifact: string
	element: ElementContext
	// where the pin sits, as a share of the element's box
	x: number
	y: number
	body: string
}

export interface ChatContext {
	artifact?: { doctype: string; name: string; title: string; path: string }
	selection?: ElementContext
	comments?: { n: number; comment: string; element: ElementContext; artifact?: { doctype: string; name: string } }[]
}

export interface ContextChip {
	key: string
	icon?: string
	badge?: number
	label: string
	title: string
}

export const selection = shallowRef<ElementContext | null>(null)
export const commenting = ref(false)
export const comments = ref<Comment[]>([])
// the pin whose popover is open: a new one, or a pinned comment being edited
export const draft = ref<Omit<Comment, "key"> & { key?: number } | null>(null)

export function describeElement(editor: ArtifactEditor, element: PreviewElement): ElementContext {
	const text = editor.textNode(element.id)?.innerText.replace(/\s+/g, " ").trim()
	return { id: element.id, label: element.label, ...(text ? { text: text.slice(0, 300) } : {}) }
}

let keys = 0
export function closeDraft(save: boolean) {
	const open = draft.value
	if (!open) return
	draft.value = null
	const body = open.body.trim()
	const pinned = comments.value.find((comment) => comment.key === open.key)
	if (!save) return
	if (pinned) {
		if (body) pinned.body = body
		else removeComment(pinned.key)
	} else if (body) {
		comments.value.push({ ...open, key: ++keys, body })
	}
}

export function removeComment(key: number) {
	comments.value = comments.value.filter((comment) => comment.key !== key)
}

const artifactKey = (doctype: string, name: string) => `${doctype}/${name}`

export function chatContext(open: { doctype: string; name: string; title: string; path: string } | null): ChatContext | null {
	const context: ChatContext = {}
	if (open) context.artifact = open
	if (open && selection.value) context.selection = selection.value
	if (comments.value.length) {
		context.comments = comments.value.map((comment, i) => {
			const [doctype, ...name] = comment.artifact.split("/")
			const elsewhere = !open || comment.artifact !== artifactKey(open.doctype, open.name)
			return {
				n: i + 1,
				comment: comment.body,
				element: comment.element,
				...(elsewhere ? { artifact: { doctype, name: name.join("/") } } : {}),
			}
		})
	}
	if (!Object.keys(context).length) return null
	carried.set(context, comments.value.map((comment) => comment.key))
	return context
}

const carried = new WeakMap<ChatContext, number[]>()
// the comments a sent message carried leave the preview
export function clearSent(context: ChatContext | null) {
	const sent = (context && carried.get(context)) ?? []
	comments.value = comments.value.filter((comment) => !sent.includes(comment.key))
}

export const pendingChips = (): ContextChip[] =>
	comments.value.map((comment, i) => ({
		key: String(comment.key),
		badge: i + 1,
		label: comment.body,
		title: `${comment.element.label}: ${comment.body}`,
	}))

export function contextChips(context: ChatContext): ContextChip[] {
	const chips: ContextChip[] = []
	if (context.artifact)
		chips.push({
			key: "artifact",
			icon: artifactIcon({ route: context.artifact.path }),
			label: context.artifact.title,
			title: `${context.artifact.doctype} ${context.artifact.name}`,
		})
	if (context.selection)
		chips.push({
			key: "selection",
			icon: "lucide-square-mouse-pointer",
			label: context.selection.label,
			title: context.selection.text ? `${context.selection.label}: ${context.selection.text}` : context.selection.label,
		})
	for (const comment of context.comments ?? [])
		chips.push({ key: `comment:${comment.n}`, badge: comment.n, label: comment.comment, title: `${comment.element.label}: ${comment.comment}` })
	return chips
}
