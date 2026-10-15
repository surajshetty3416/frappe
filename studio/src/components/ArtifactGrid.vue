<template>
	<!-- an artifact opens with the chat that made it beside it -->
	<div v-if="artifactView === 'grid'" class="grid grid-cols-[repeat(auto-fill,minmax(13rem,1fr))] gap-3">
		<RouterLink
			v-for="artifact in artifacts"
			:key="`${artifact.doctype}/${artifact.name}`"
			:to="artifact.route"
			class="flex min-w-0 flex-col gap-3 rounded-6 border border-outline-gray-2 bg-surface-base p-3 transition-colors hover:border-outline-gray-3 hover:bg-surface-gray-1"
		>
			<span class="grid size-8 place-items-center rounded-4 bg-surface-gray-2 text-ink-gray-6">
				<span :class="artifactIcon(artifact)" class="size-4" />
			</span>
			<span class="flex min-w-0 flex-col gap-0.5">
				<span class="truncate text-base font-medium text-ink-gray-8">{{ artifact.title }}</span>
				<span class="truncate text-sm text-ink-gray-5">{{ artifact.label }} · {{ dayjs(artifact.modified).fromNow() }}</span>
				<span v-if="showProject && artifact.project" class="truncate text-sm text-ink-gray-4">{{ artifact.project.title }}</span>
			</span>
		</RouterLink>
	</div>
	<section v-else class="flex flex-col">
		<ProjectRow
			v-for="artifact in artifacts"
			:key="`${artifact.doctype}/${artifact.name}`"
			:to="artifact.route"
			:title="artifact.title"
			:icon="artifactIcon(artifact)"
		>
			<template #suffix>
				<span v-if="showProject" class="w-36 truncate text-right">{{ artifact.project?.title }}</span>
				<span class="w-28 truncate text-right">{{ artifact.label }}</span>
				<span class="w-28 whitespace-nowrap text-right text-ink-gray-4">{{ dayjs(artifact.modified).fromNow() }}</span>
			</template>
		</ProjectRow>
	</section>
</template>

<script setup lang="ts">
import { dayjs } from "frappe-ui"
import { RouterLink } from "vue-router"

import { artifactIcon } from "../artifacts"
import { artifactView } from "../layout"
import type { ProjectArtifact } from "../projects"
import ProjectRow from "./project/ProjectRow.vue"

// artifacts as cards or rows, as the person last chose; `showProject` names the project that made each
defineProps<{ artifacts: ProjectArtifact[]; showProject?: boolean }>()
</script>
