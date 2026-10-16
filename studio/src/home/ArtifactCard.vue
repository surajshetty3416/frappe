<template>
	<RouterLink
		:to="viewRoute(artifact)"
		class="flex min-w-0 items-center gap-3 rounded-2 border border-outline-gray-2 bg-surface-base p-3 transition-colors hover:border-outline-gray-3 hover:bg-surface-gray-1"
	>
		<span class="grid size-9 shrink-0 place-items-center rounded-4 bg-surface-gray-2 text-ink-gray-6">
			<span :class="artifactIcon(artifact)" class="size-4" />
		</span>
		<span class="flex min-w-0 flex-col gap-0.5">
			<span class="truncate text-base font-medium text-ink-gray-8">{{ artifact.title }}</span>
			<span class="truncate text-sm text-ink-gray-5">{{ artifact.label }} · {{ dayjs(artifact.modified).fromNow() }}</span>
		</span>
	</RouterLink>
</template>

<script setup lang="ts">
import { dayjs } from "frappe-ui"
import { RouterLink } from "vue-router"

import { artifactIcon } from "../artifacts"
import { type HomeArtifact, viewRoute } from "./home"

defineProps<{ artifact: HomeArtifact }>()
</script>
