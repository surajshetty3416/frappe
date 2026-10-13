<template>
	<section data-layer="shell" class="flex h-full min-w-0 flex-col bg-surface-base">
		<div class="flex h-10 shrink-0 items-center gap-1 overflow-x-auto border-b border-outline-gray-1 px-2" role="tablist">
			<div
				v-for="tab in tabs"
				:key="tabKey(tab)"
				role="tab"
				:aria-selected="isActive(tab)"
				:title="tab.title"
				class="group flex h-7 min-w-0 max-w-[200px] shrink-0 cursor-pointer items-center gap-1.5 rounded-4 pl-2 pr-0.5 text-sm transition-colors"
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

		<div v-if="artifact" class="flex h-11 shrink-0 items-center gap-2 border-b border-outline-gray-1 pl-3 pr-2">
			<div class="flex min-w-0 flex-1 items-center gap-2">
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
						class="truncate rounded-4 px-1 py-0.5 text-base font-medium text-ink-gray-8"
						:class="editor ? 'cursor-text hover:bg-surface-gray-2' : ''"
						@click="startRename"
						>{{ title }}</span
					>
				</Tooltip>
				<span v-if="status" class="flex shrink-0 items-center gap-1.5 text-sm text-ink-gray-5">
					<span class="size-1.5 rounded-full" :class="STATUS_DOT[status.theme]" />
					{{ status.label }}
				</span>
			</div>
			<div class="flex shrink-0 items-center gap-0.5">
				<Button
					variant="ghost"
					icon="lucide-message-square-plus"
					:tooltip="editor ? (commenting ? 'Stop commenting' : 'Comment') : 'This artifact takes no comments yet'"
					aria-label="Comment"
					:disabled="!editor"
					:class="commenting ? '!bg-surface-gray-3' : ''"
					@click="commenting = !commenting"
				/>
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

		<div class="relative min-h-0 flex-1">
			<SelectionLayer :editor="editor" :artifact="artifactKey" :covered="!!openDrawer" :data-layer="route.matched[0]?.meta.layer">
				<slot />
			</SelectionLayer>
			<EditorDrawer
				v-if="artifact"
				:drawer="openDrawer"
				:doctype="artifact.doctype"
				:name="artifact.name"
				:editor="editor"
				:label="drawers.find((drawer) => drawer.name === openDrawer)?.label ?? ''"
				@close="openDrawer = null"
			/>
		</div>
	</section>
</template>

<script setup lang="ts">
import { Button, TextInput, Tooltip, toast } from "frappe-ui"
import { computed, nextTick, onBeforeUnmount, onMounted, ref, shallowRef, watch } from "vue"
import { useRoute, useRouter } from "vue-router"

import { getArtifactInfo, routeArtifact } from "../artifacts"
import { commenting } from "../context"
import type { ArtifactEditor } from "../editor"
import { layers } from "../layers"
import { onDocUpdate } from "../realtime"
import { type Tab, closeTab, findTab, openTab, tabKey, tabs } from "../tabs"
import EditorDrawer from "./EditorDrawer.vue"
import SelectionLayer from "./SelectionLayer.vue"

const STATUS_DOT = { gray: "bg-surface-gray-5", green: "bg-surface-green-7", orange: "bg-surface-amber-6" }

const route = useRoute()
const router = useRouter()

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

function onKeydown(event: KeyboardEvent) {
	if (event.key === "Escape" && openDrawer.value && !event.defaultPrevented) {
		openDrawer.value = null
		event.preventDefault()
	}
}
onMounted(() => window.addEventListener("keydown", onKeydown))
onBeforeUnmount(() => window.removeEventListener("keydown", onKeydown))
</script>
