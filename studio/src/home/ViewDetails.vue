<template>
	<div class="flex flex-col gap-5 p-4">
		<div class="flex items-center gap-3">
			<span class="grid size-9 shrink-0 place-items-center rounded-4 bg-surface-gray-2 text-ink-gray-6">
				<span :class="artifactIcon(view)" class="size-4" />
			</span>
			<div class="min-w-0">
				<p class="truncate text-base font-medium text-ink-gray-8">{{ view.title }}</p>
				<p class="text-sm text-ink-gray-5">{{ view.label }}</p>
			</div>
		</div>
		<dl v-if="info" class="grid grid-cols-[auto,1fr] gap-x-4 gap-y-2 text-sm">
			<dt class="text-ink-gray-5">Made by</dt>
			<dd class="truncate text-ink-gray-8">{{ info.owner }}</dd>
			<dt class="text-ink-gray-5">Created</dt>
			<dd class="text-ink-gray-8">{{ dayjs(info.creation).fromNow() }}</dd>
			<dt class="text-ink-gray-5">Updated</dt>
			<dd class="text-ink-gray-8">{{ dayjs(info.modified).fromNow() }}</dd>
		</dl>
		<section v-if="versions?.length" class="flex flex-col gap-2">
			<h3 class="text-sm font-medium text-ink-gray-5">Changes</h3>
			<ul class="flex flex-col gap-2">
				<li v-for="version in versions.slice(0, 8)" :key="version.name" class="flex items-start gap-2 text-sm">
					<span :class="version.source === 'Agent' ? 'lucide-sparkles' : 'lucide-user'" class="mt-0.5 size-3.5 shrink-0 text-ink-gray-4" />
					<span class="min-w-0 flex-1 text-ink-gray-7">{{ version.label }}</span>
					<span class="shrink-0 text-ink-gray-4">{{ dayjs(version.creation).fromNow() }}</span>
				</li>
			</ul>
		</section>
		<div v-if="view.can_write" class="flex flex-col gap-2 border-t border-outline-gray-1 pt-4">
			<Button variant="solid" icon-left="lucide-pencil" label="Edit in Studio" :route="view.route" />
			<Button v-if="info?.chat" icon-left="lucide-message-square" label="Open the chat that made it" :route="`/studio/chat/${info.chat.name}`" />
		</div>
	</div>
</template>

<script setup lang="ts">
import { Button, dayjs } from "frappe-ui"
import { ref, watch } from "vue"

import { type ArtifactInfo, type Version, artifactIcon, getArtifactInfo, getVersions } from "../artifacts"
import type { View } from "./home"

const props = defineProps<{ view: View }>()

const info = ref<ArtifactInfo | null>(null)
const versions = ref<Version[] | null>(null)
watch(
	() => `${props.view.doctype}/${props.view.name}`,
	() => {
		info.value = null
		versions.value = null
		const { doctype, name } = props.view
		getArtifactInfo(doctype, name).then((value) => (info.value = value)).catch(() => {})
		getVersions(doctype, name).then((value) => (versions.value = value)).catch(() => {})
	},
	{ immediate: true }
)
</script>
