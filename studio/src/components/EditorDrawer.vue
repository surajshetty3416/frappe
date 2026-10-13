<template>
	<Transition
		enter-active-class="transition duration-150 ease-out"
		enter-from-class="translate-x-4 opacity-0"
		leave-active-class="transition duration-100 ease-out"
		leave-to-class="translate-x-4 opacity-0"
	>
		<aside
			v-if="drawer"
			data-editor-drawer
			class="absolute inset-y-0 right-0 z-20 flex w-[340px] flex-col overflow-hidden border-l border-outline-gray-1 bg-surface-base"
		>
			<header class="flex h-10 shrink-0 items-center justify-between border-b border-outline-gray-1 pl-4 pr-2">
				<h2 class="text-base font-medium text-ink-gray-8">{{ label }}</h2>
				<div class="flex items-center gap-0.5">
					<Button v-if="drawer === 'code'" variant="ghost" icon="lucide-copy" tooltip="Copy" @click="copyCode" />
					<Button variant="ghost" icon="lucide-x" tooltip="Close (Esc)" @click="emit('close')" />
				</div>
			</header>

			<div v-if="drawer === 'versions'" class="min-h-0 flex-1 overflow-y-auto p-2">
				<div v-if="versions.loading && !versions.list.length" class="flex flex-col gap-3 p-2">
					<div v-for="i in 4" :key="i" class="flex gap-3">
						<Skeleton class="size-6 rounded-full" />
						<div class="flex flex-1 flex-col gap-1.5"><Skeleton class="h-3 w-3/4" /><Skeleton class="h-3 w-1/3" /></div>
					</div>
				</div>
				<div v-else-if="!versions.list.length" class="flex flex-col items-center px-6 py-12 text-center">
					<span class="lucide-history size-5 text-ink-gray-4" />
					<p class="mt-3 text-base font-medium text-ink-gray-8">No versions yet</p>
					<p class="mt-1 text-p-sm text-ink-gray-5">Each change, yours or the assistant's, saves a version you can go back to.</p>
				</div>
				<ol v-else class="m-0 flex list-none flex-col p-0">
					<li
						v-for="(version, index) in versions.list"
						:key="version.name"
						class="group flex items-start gap-3 rounded-lg px-2 py-2.5 hover:bg-surface-gray-1"
					>
						<span
							class="mt-0.5 grid size-6 shrink-0 place-items-center rounded-full"
							:class="version.source === 'Agent' ? 'bg-surface-gray-2 text-ink-gray-6' : ''"
						>
							<span v-if="version.source === 'Agent'" class="lucide-sparkles size-3.5" />
							<Avatar v-else :label="version.owner" size="sm" />
						</span>
						<div class="min-w-0 flex-1">
							<p class="truncate text-sm text-ink-gray-8" :title="version.label">{{ version.label }}</p>
							<p class="mt-0.5 text-xs text-ink-gray-5" :title="dayjs(version.creation).format('D MMM YYYY, h:mm a')">
								{{ dayjs(version.creation).fromNow() }}
							</p>
						</div>
						<span v-if="index === 0" class="mt-0.5 shrink-0 rounded-md bg-surface-gray-2 px-1.5 py-0.5 text-xs text-ink-gray-6">Current</span>
						<Button
							v-else
							size="sm"
							label="Restore"
							class="shrink-0 opacity-0 group-hover:opacity-100 focus-visible:opacity-100"
							:loading="versions.restoring === version.name"
							@click="restore(version.name)"
						/>
					</li>
				</ol>
			</div>

			<dl v-else-if="drawer === 'details'" class="min-h-0 flex-1 overflow-y-auto px-4 py-3">
				<div v-for="row in details" :key="row.label" class="flex items-baseline gap-3 py-1.5">
					<dt class="w-24 shrink-0 text-sm text-ink-gray-5">{{ row.label }}</dt>
					<dd class="min-w-0 flex-1 break-words text-sm text-ink-gray-8">
						<a v-if="row.href" :href="row.href" target="_blank" class="underline decoration-outline-gray-3 underline-offset-2 hover:decoration-outline-gray-5">{{ row.value }}</a>
						<template v-else>{{ row.value }}</template>
					</dd>
				</div>
			</dl>

			<div v-else-if="drawer === 'code' && code" class="min-h-0 flex-1 overflow-auto bg-surface-gray-1">
				<pre class="p-4 font-mono text-xs leading-5 text-ink-gray-8">{{ code.content }}</pre>
			</div>
		</aside>
	</Transition>
</template>

<script setup lang="ts">
import { Avatar, Button, Skeleton, dayjs, toast } from "frappe-ui"
import { computed, onBeforeUnmount, reactive, ref, watch } from "vue"

import { type ArtifactInfo, type Version, artifactLabel, getArtifactInfo, getVersions, restoreVersion } from "../artifacts"
import type { ArtifactEditor } from "../editor"
import { onDocUpdate } from "../realtime"

const props = defineProps<{
	drawer: string | null
	doctype: string
	name: string
	label: string
	editor: ArtifactEditor | null
}>()
const emit = defineEmits<{ close: [] }>()

const versions = reactive({ list: [] as Version[], loading: false, restoring: null as string | null })
async function loadVersions() {
	versions.loading = true
	try {
		versions.list = await getVersions(props.doctype, props.name)
	} finally {
		versions.loading = false
	}
}
async function restore(version: string) {
	versions.restoring = version
	try {
		await restoreVersion(version)
		await Promise.all([loadVersions(), props.editor?.reload()])
		toast.success("Version restored")
	} catch (error) {
		toast.error((error as Error)?.message || "Could not restore the version")
	} finally {
		versions.restoring = null
	}
}

const info = ref<ArtifactInfo | null>(null)
const details = computed(() => {
	const rows = [{ label: "Type", value: artifactLabel(props.doctype) }]
	rows.push(...(props.editor?.details() ?? []))
	if (info.value) {
		rows.push(
			{ label: "Created by", value: info.value.owner },
			{ label: "Created", value: dayjs(info.value.creation).format("D MMM YYYY, h:mm a") },
			{ label: "Last changed", value: dayjs(info.value.modified).fromNow() }
		)
	}
	rows.push({ label: "ID", value: props.name })
	return rows
})

const code = computed(() => (props.drawer === "code" ? props.editor?.code() : null))
function copyCode() {
	if (!code.value) return
	navigator.clipboard.writeText(code.value.content)
	toast.success("Copied")
}

function load() {
	if (props.drawer === "versions") loadVersions()
	if (props.drawer === "details") getArtifactInfo(props.doctype, props.name).then((value) => (info.value = value))
}
watch(() => [props.drawer, props.doctype, props.name], load, { immediate: true })

// a save by anyone adds or extends a version
let stop: (() => void) | null = null
watch(
	() => [props.doctype, props.name],
	() => {
		stop?.()
		stop = onDocUpdate(props.doctype, props.name, () => props.drawer && load())
	},
	{ immediate: true }
)
onBeforeUnmount(() => stop?.())
</script>
