<template>
	<div data-layer="shell" class="h-full overflow-y-auto">
		<div class="mx-auto flex w-full max-w-[960px] flex-col gap-6 px-6 pb-32 pt-12">
			<h1 class="text-3xl font-semibold text-ink-gray-9">{{ kind.title }}</h1>
			<div v-if="!artifacts" class="flex h-24 items-center justify-center">
				<LoadingIndicator class="size-4 text-ink-gray-5" />
			</div>
			<p v-else-if="!artifacts.length" class="text-base text-ink-gray-5">No {{ kind.title.toLowerCase() }} yet.</p>
			<div v-else class="grid grid-cols-[repeat(auto-fill,minmax(16rem,1fr))] gap-3">
				<ArtifactCard v-for="artifact in artifacts" :key="`${artifact.doctype}/${artifact.name}`" :artifact="artifact" />
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { LoadingIndicator } from "frappe-ui"
import { computed, ref, watch } from "vue"
import { useRoute } from "vue-router"

import { artifactKind, artifactKinds } from "../artifacts"
import { type ProjectArtifact, getArtifacts } from "../projects"
import ArtifactCard from "./ArtifactCard.vue"
import { openView } from "./home"

const route = useRoute()
const kind = computed(() => artifactKind(route) ?? artifactKinds[0])

const artifacts = ref<ProjectArtifact[] | null>(null)
watch(
	kind,
	async (shown) => {
		artifacts.value = null
		openView.value = null
		document.title = shown.title
		const list = await getArtifacts(shown.doctypes, null).catch(() => [])
		if (kind.value === shown) artifacts.value = list
	},
	{ immediate: true }
)
</script>
