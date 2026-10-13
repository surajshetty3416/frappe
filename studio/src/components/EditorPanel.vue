<template>
	<section data-layer="shell" class="flex h-full min-w-0 flex-col bg-surface-base">
		<div class="flex h-10 shrink-0 items-center border-b border-outline-gray-1">
			<!-- tabs keep a readable width; the strip scrolls, and the ones out of view fold into a menu -->
			<div
				ref="strip"
				class="flex h-full min-w-0 flex-1 items-center gap-1 overflow-x-auto px-2 [scrollbar-width:none]"
				:style="{ maskImage: stripMask, WebkitMaskImage: stripMask }"
				role="tablist"
				@scroll="measureTabs"
				@wheel="scrollTabs"
			>
				<div
					v-for="tab in tabs"
					:key="tabKey(tab)"
					:data-tab="tabKey(tab)"
					role="tab"
					:aria-selected="isActive(tab)"
					:title="tab.title"
					class="group flex h-7 min-w-32 max-w-60 shrink-0 cursor-pointer items-center gap-1.5 rounded-4 pl-2 pr-0.5 text-sm transition-colors"
					:class="isActive(tab) ? 'bg-surface-gray-2 text-ink-gray-8' : 'text-ink-gray-6 hover:bg-surface-gray-1'"
					@click="router.push(tab.path)"
					@auxclick.middle="close(tab)"
				>
					<span :class="tab.icon" class="size-4 shrink-0 text-ink-gray-5" />
					<span class="min-w-0 flex-1 truncate">{{ tab.title }}</span>
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
			<Dropdown v-if="outOfView.length" :options="outOfViewOptions" align="end">
				<Button variant="ghost" class="mr-2 shrink-0" :label="`+${outOfView.length}`" :tooltip="'More tabs'" />
			</Dropdown>
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
				<!-- the title stays whole; the status truncates, and a title wider than the bar truncates last -->
				<Tooltip v-else :text="editor ? 'Rename' : undefined" :disabled="!editor">
					<span
						class="block max-w-full shrink-0 truncate rounded-4 px-1 py-0.5 text-base font-medium text-ink-gray-8"
						:class="editor ? 'cursor-text hover:bg-surface-gray-2' : ''"
						@click="startRename"
						>{{ title }}</span
					>
				</Tooltip>
				<span v-if="status" class="flex min-w-0 items-center gap-1.5 whitespace-nowrap text-sm text-ink-gray-5">
					<span class="size-1.5 shrink-0 rounded-full" :class="STATUS_DOT[status.theme]" />
					<span class="truncate">{{ status.label }}</span>
				</span>
			</div>
			<div class="flex shrink-0 items-center gap-0.5">
				<Tooltip v-if="saving" text="Saving">
					<span class="mr-1.5 flex size-4 items-center" aria-label="Saving"><LoadingIndicator class="size-3.5 text-ink-gray-5" /></span>
				</Tooltip>
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
				<Button
					v-if="editor && !contextRow"
					variant="ghost"
					icon="lucide-message-square-plus"
					:tooltip="commenting ? 'Stop commenting' : 'Comment'"
					aria-label="Comment"
					:class="commenting ? '!bg-surface-gray-3' : ''"
					@click="toggleCommenting"
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

		<SelectionLayer
			class="min-h-0 flex-1"
			:editor="editor"
			:artifact="artifactKey"
			:covered="!!openDrawer"
			:layer="layerName"
			:hide-idle="!contextRow"
		>
			<template #idle>
				<div class="flex min-w-0 flex-1 items-center gap-2">
					<TabButtons
						v-if="views.length"
						variant="ghost"
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
import { Button, Dropdown, LoadingIndicator, TabButtons, TextInput, Tooltip, toast } from "frappe-ui"
import { computed, nextTick, onBeforeUnmount, onMounted, ref, shallowRef, watch } from "vue"
import { useRoute, useRouter } from "vue-router"

import { getArtifactInfo, routeArtifact } from "../artifacts"
import { commenting } from "../context"
import { type ArtifactEditor, type EditorMode, editorMode } from "../editor"
import { layers } from "../layers"
import { overlayOpen } from "../layout"
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
// a layer's own view beside the chat, such as the Data overview, has no artifact; its tab is keyed by its path
const openKey = computed(() => artifactKey.value || (route.matched.some((match) => match.meta.artifact) ? tabKey({ doctype: "", name: route.path }) : ""))
const isActive = (tab: Tab) => tabKey(tab) === openKey.value

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
	() => [openKey.value, route.fullPath],
	async () => {
		const open = artifact.value
		const layer = layers.find((layer) => layer.name === route.matched[0]?.meta.layer)
		const chat = typeof route.query.chat === "string" ? route.query.chat : null
		if (!open) {
			if (openKey.value)
				openTab({ doctype: "", name: route.path, title: layer?.title ?? "", icon: layer?.icon ?? "lucide-file", path: route.fullPath, chat })
			return
		}
		openTab({
			doctype: open.doctype,
			name: open.name,
			title: findTab(open.doctype, open.name)?.title ?? open.name,
			icon: layer?.icon ?? "lucide-file",
			path: route.fullPath,
			chat,
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
const saving = computed(() => editor.value?.saving?.() ?? false)
const action = computed(() => editor.value?.primaryAction() ?? null)
const views = computed(() => editor.value?.views?.() ?? [])
const barControls = computed(() => editor.value?.barControls?.() ?? null)

// an editor with nothing to switch, set or select has no idle context row; its Comment sits in the artifact bar
const contextRow = computed(() => views.value.length > 0 || Boolean(barControls.value) || modes.value.includes("edit"))
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

const strip = ref<HTMLElement | null>(null)
const outOfView = ref<Tab[]>([])
// a strip scrolled past a tab fades on that side, so a tab cut mid-word reads as more to scroll; the fade
// spans half a tab, since a narrower one over the strip's padding leaves the cut word whole
const clipped = ref({ left: false, right: false })
const FADE = "64px"
const stripMask = computed(() => {
	const { left, right } = clipped.value
	if (!left && !right) return undefined
	return `linear-gradient(to right, ${left ? `transparent, black ${FADE}` : "black"}, ${right ? `black calc(100% - ${FADE}), transparent` : "black"})`
})
const outOfViewOptions = computed(() =>
	outOfView.value.map((tab) => ({ label: tab.title, icon: tab.icon, onClick: () => router.push(tab.path) }))
)
function measureTabs() {
	const el = strip.value
	if (!el) return
	const box = el.getBoundingClientRect()
	clipped.value = { left: el.scrollLeft > 1, right: el.scrollLeft + el.clientWidth < el.scrollWidth - 1 }
	outOfView.value = tabs.value.filter((tab) => {
		const rect = el.querySelector(`[data-tab="${CSS.escape(tabKey(tab))}"]`)?.getBoundingClientRect()
		return rect && (rect.left < box.left - 1 || rect.right > box.right + 1)
	})
}
// a mouse wheel scrolls the strip sideways
function scrollTabs(event: WheelEvent) {
	if (!strip.value || Math.abs(event.deltaY) <= Math.abs(event.deltaX)) return
	strip.value.scrollLeft += event.deltaY
	event.preventDefault()
}
// the open tab stays in view as tabs come and go, and as the strip narrows for the menu
function revealActive() {
	strip.value?.querySelector(`[data-tab="${CSS.escape(openKey.value)}"]`)?.scrollIntoView({ block: "nearest", inline: "nearest" })
	measureTabs()
}
watch(
	() => [tabs.value.map((tab) => tabKey(tab) + tab.title).join(), openKey.value],
	() => nextTick(revealActive),
	{ immediate: true }
)
const stripResize = new ResizeObserver(revealActive)
watch(strip, (el, old) => {
	if (old) stripResize.unobserve(old)
	if (el) stripResize.observe(el)
})
onBeforeUnmount(() => stripResize.disconnect())

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
	if (event.defaultPrevented || (event.key === "Escape" && overlayOpen())) return
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
