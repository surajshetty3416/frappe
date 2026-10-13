<template>
	<section data-layer="shell" class="flex h-full min-w-0 flex-col bg-surface-base">
		<div class="flex h-10 shrink-0 items-center gap-1 overflow-x-auto border-b border-outline-gray-1 px-2" role="tablist">
			<div
				v-for="tab in tabs"
				:key="tabKey(tab)"
				role="tab"
				:aria-selected="isActive(tab)"
				:title="tab.title"
				class="group flex h-7 min-w-[96px] max-w-[280px] shrink cursor-pointer items-center gap-1.5 rounded-4 pl-2 pr-0.5 text-sm transition-colors"
				:class="isActive(tab) ? 'bg-surface-gray-2 text-ink-gray-8' : 'text-ink-gray-6 hover:bg-surface-gray-1'"
				@click="router.push(tab.path)"
				@auxclick.middle="close(tab)"
			>
				<span :class="tab.icon" class="size-4 shrink-0 text-ink-gray-5" />
				<span class="truncate">{{ tab.title }}</span>
				<Button
					size="xs"
					variant="ghost"
					icon="lucide-x"
					class="shrink-0"
					:class="isActive(tab) ? '' : 'opacity-0 group-hover:opacity-100'"
					:tooltip="'Close'"
					@click.stop="close(tab)"
				/>
			</div>
		</div>

		<div v-if="artifact" data-artifact-bar class="flex h-11 shrink-0 items-center gap-2 border-b border-outline-gray-1 pl-3 pr-2">
			<div class="flex min-w-0 flex-1 items-center gap-2 overflow-hidden">
				<TextInput
					v-if="renaming"
					ref="titleInput"
					v-model="draftTitle"
					size="sm"
					class="w-72"
					@keydown.enter="commitRename"
					@keydown.esc.stop="renaming = false"
					@blur="commitRename"
				/>
				<Tooltip v-else :text="editor ? 'Rename' : undefined" :disabled="!editor">
					<span
						class="block min-w-0 truncate rounded-4 px-1 py-0.5 text-base font-medium text-ink-gray-8"
						:class="editor ? 'cursor-text hover:bg-surface-gray-2' : ''"
						@click="startRename"
						>{{ title }}</span
					>
				</Tooltip>
				<span v-if="status" class="flex shrink-0 items-center gap-1.5 whitespace-nowrap text-sm text-ink-gray-5">
					<span class="size-1.5 shrink-0 rounded-full" :class="STATUS_DOT[status.theme]" />
					<span>{{ status.label }}</span>
				</span>
			</div>
			<div class="flex shrink-0 items-center gap-0.5">
				<Button
					v-for="drawer in drawers"
					:key="drawer.name"
					variant="ghost"
					:icon="drawer.icon"
					:tooltip="drawer.disabled ? `${drawer.label} is not available here` : drawer.label"
					:aria-label="drawer.label"
					:disabled="drawer.disabled"
					:class="openDrawer === drawer.name ? '!bg-surface-gray-3' : ''"
					@click="toggleDrawer(drawer.name)"
				/>
				<template v-if="action">
					<div class="mx-1.5 h-4 w-px bg-surface-gray-3" />
					<Button
						variant="solid"
						:label="action.label"
						:icon-left="action.icon"
						:disabled="action.disabled"
						:loading="running"
						@click="runAction"
					/>
				</template>
			</div>
		</div>

		<SelectionLayer class="min-h-0 flex-1" :editor="editor" :artifact="artifactKey" :covered="!!openDrawer" :layer="layerName">
			<template #idle>
				<div class="flex min-w-0 flex-1 items-center gap-2">
					<TabButtons
						v-if="views.length"
						class="shrink-0"
						:options="views.map((view) => ({ value: view.name, label: view.label }))"
						:model-value="views.find((view) => view.active)?.name"
						@update:model-value="(name) => views.find((view) => view.name === name)?.open()"
					/>
					<LayerComponent v-if="barControls" :mount="barControls" :layer="layerName" />
					<span v-if="!views.length && !barControls && editorMode === 'edit'" class="truncate text-sm text-ink-gray-5">
						Select an element to change it
					</span>
				</div>
				<div class="flex shrink-0 items-center gap-0.5">
					<div v-if="modes.length > 1" role="radiogroup" aria-label="Mode" class="flex items-center gap-0.5">
						<Button
							v-for="mode in MODES"
							:key="mode.value"
							role="radio"
							variant="ghost"
							:icon="mode.icon"
							:tooltip="mode.label"
							:aria-label="mode.label"
							:aria-checked="editorMode === mode.value"
							:class="editorMode === mode.value ? '!bg-surface-gray-3 !text-ink-gray-8' : ''"
							@click="setMode(mode.value)"
						/>
					</div>
					<Button
						variant="ghost"
						icon="lucide-message-square-plus"
						:tooltip="commenting ? 'Stop commenting' : 'Comment'"
						aria-label="Comment"
						:class="commenting ? '!bg-surface-gray-3' : ''"
						@click="toggleCommenting"
					/>
				</div>
			</template>
			<slot />
			<template #over>
				<EditorDrawer
					v-if="artifact"
					:drawer="openDrawer"
					:doctype="artifact.doctype"
					:name="artifact.name"
					:editor="editor"
					:layer="layerName"
					:label="drawers.find((drawer) => drawer.name === openDrawer)?.label ?? ''"
					@close="openDrawer = null"
				/>
			</template>
		</SelectionLayer>
	</section>
</template>

<script setup lang="ts">
import { Button, TabButtons, TextInput, Tooltip, toast } from "frappe-ui"
import { computed, nextTick, onBeforeUnmount, onMounted, ref, shallowRef, watch } from "vue"
import { useRoute, useRouter } from "vue-router"

import { getArtifactInfo, routeArtifact } from "../artifacts"
import { commenting } from "../context"
import { type ArtifactEditor, type EditorMode, editorMode } from "../editor"
import { layers } from "../layers"
import { onDocUpdate } from "../realtime"
import { type Tab, closeTab, findTab, openTab, tabKey, tabs } from "../tabs"
import EditorDrawer from "./EditorDrawer.vue"
import LayerComponent from "./LayerComponent.vue"
import SelectionLayer from "./SelectionLayer.vue"

const STATUS_DOT = { gray: "bg-surface-gray-5", green: "bg-surface-green-7", orange: "bg-surface-amber-6" }

const MODES = [
	{ value: "edit", label: "Edit", icon: "lucide-mouse-pointer-2" },
	{ value: "preview", label: "Preview (Esc to edit)", icon: "lucide-eye" },
] as const

const route = useRoute()
const router = useRouter()
const layerName = computed(() => route.matched[0]?.meta.layer as string | undefined)

const artifact = computed(() => routeArtifact(route))
const artifactKey = computed(() => (artifact.value ? tabKey(artifact.value) : ""))
const isActive = (tab: Tab) => tabKey(tab) === artifactKey.value

const editor = shallowRef<ArtifactEditor | null>(null)
watch(
	() => artifact.value?.editor,
	async (load) => {
		editor.value = load ? (await load()).default : null
	},
	{ immediate: true }
)

// an artifact the route opens joins the tabs, or focuses its tab
watch(
	() => [artifactKey.value, route.fullPath],
	async () => {
		const open = artifact.value
		if (!open) return
		const layer = layers.find((layer) => layer.name === route.matched[0]?.meta.layer)
		openTab({
			doctype: open.doctype,
			name: open.name,
			title: findTab(open.doctype, open.name)?.title ?? open.name,
			icon: layer?.icon ?? "lucide-file",
			path: route.fullPath,
			chat: typeof route.query.chat === "string" ? route.query.chat : null,
		})
		if (!open.editor) {
			const info = await getArtifactInfo(open.doctype, open.name).catch(() => null)
			const tab = findTab(open.doctype, open.name)
			if (tab && info) tab.title = info.title
		}
	},
	{ immediate: true }
)

const title = computed(() => editor.value?.title() || (artifact.value && findTab(artifact.value.doctype, artifact.value.name)?.title) || "")
watch(title, (value) => {
	const tab = artifact.value && findTab(artifact.value.doctype, artifact.value.name)
	if (tab && value && editor.value) tab.title = value
})
const status = computed(() => editor.value?.status() ?? null)
const action = computed(() => editor.value?.primaryAction() ?? null)
const views = computed(() => editor.value?.views?.() ?? [])
const barControls = computed(() => editor.value?.barControls?.() ?? null)

const modes = computed<EditorMode[]>(() => (editor.value ? (editor.value.modes ?? ["edit", "preview"]) : []))
// each artifact opens in its layer's first mode
watch(
	() => [artifactKey.value, editor.value] as const,
	() => (editorMode.value = modes.value[0] ?? "edit"),
	{ immediate: true }
)
function setMode(mode: EditorMode) {
	editorMode.value = mode
	if (mode === "preview") commenting.value = false
}
function toggleCommenting() {
	commenting.value = !commenting.value
	if (commenting.value) editorMode.value = "edit"
}

const drawers = computed(() => [
	{ name: "versions", label: "Versions", icon: "lucide-history", disabled: false },
	{ name: "details", label: "Details", icon: "lucide-info", disabled: false },
	{ name: "code", label: "Code", icon: "lucide-code-xml", disabled: !editor.value },
])
const openDrawer = ref<string | null>(null)
watch(editor, (open) => {
	if (!open) commenting.value = false
})
onBeforeUnmount(() => (commenting.value = false))
const toggleDrawer = (name: string) => (openDrawer.value = openDrawer.value === name ? null : name)
// a closed drawer's button lets go of the focus, or it still looks pressed
watch(openDrawer, (open) => {
	const focused = document.activeElement
	if (!open && focused instanceof HTMLElement && focused.closest("[data-artifact-bar]")) focused.blur()
})

function close(tab: Tab) {
	const wasActive = isActive(tab)
	const next = closeTab(tab)
	if (!wasActive) return
	if (next) return router.push(next.path)
	const chat = route.query.chat
	router.push(typeof chat === "string" ? { name: "studio-chat", params: { session: chat } } : "/studio")
}

const renaming = ref(false)
const draftTitle = ref("")
const titleInput = ref<{ focus: () => void } | null>(null)
function startRename() {
	if (!editor.value) return
	draftTitle.value = title.value
	renaming.value = true
	nextTick(() => titleInput.value?.focus())
}
function commitRename() {
	if (!renaming.value) return
	renaming.value = false
	const value = draftTitle.value.trim()
	if (value && value !== title.value) editor.value?.rename(value)
}

const running = ref(false)
async function runAction() {
	if (!action.value) return
	running.value = true
	try {
		await action.value.run()
	} catch (error) {
		toast.error((error as Error)?.message || "That did not work")
	} finally {
		running.value = false
	}
}

// what the agent or a restore saves shows in the preview as it lands
let stopWatching: (() => void) | null = null
watch(
	() => [artifact.value?.doctype, artifact.value?.name, editor.value] as const,
	([doctype, name, open]) => {
		stopWatching?.()
		stopWatching = doctype && name && open ? onDocUpdate(doctype, name, (modified) => open.reload(modified)) : null
	},
	{ immediate: true }
)
onBeforeUnmount(() => stopWatching?.())

const typing = (target: EventTarget | null) =>
	target instanceof HTMLElement && Boolean(target.closest('input, textarea, select, [contenteditable="true"], .cm-editor'))

function onKeydown(event: KeyboardEvent) {
	if (event.defaultPrevented) return
	if (event.key === "Escape" && openDrawer.value) {
		openDrawer.value = null
		event.preventDefault()
	} else if (event.key === "Escape" && editorMode.value === "preview" && modes.value.includes("edit")) {
		editorMode.value = "edit"
		event.preventDefault()
	} else if (event.key.toLowerCase() === "z" && (event.metaKey || event.ctrlKey) && editor.value && !typing(event.target)) {
		const step = event.shiftKey ? editor.value.redo : editor.value.undo
		if (!step) return
		step()
		event.preventDefault()
	}
}
onMounted(() => window.addEventListener("keydown", onKeydown))
onBeforeUnmount(() => window.removeEventListener("keydown", onKeydown))
</script>
