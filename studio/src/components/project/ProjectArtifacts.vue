<template>
	<p v-if="!page.artifacts.length" class="px-2 py-2 text-base text-ink-gray-5">No artifacts yet.</p>
	<ArtifactGrid v-else :artifacts="page.artifacts" />
</template>

<script setup lang="ts">
import type { ProjectPage } from "../../projects"
import ArtifactGrid from "../ArtifactGrid.vue"

defineProps<{ page: ProjectPage }>()
</script>
