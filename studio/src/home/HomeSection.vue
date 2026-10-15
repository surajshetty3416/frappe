<template>
	<section class="flex flex-col gap-3">
		<div class="flex items-center gap-2">
			<h2 class="mr-auto truncate text-lg font-medium text-ink-gray-8">{{ title }}</h2>
			<Button v-if="section.type === 'embed' && section.view" variant="ghost" size="sm" label="Open" icon-right="lucide-arrow-up-right" :route="viewRoute(section.view)" />
			<slot name="actions" />
		</div>

		<p v-if="section.type !== 'browse' && section.artifacts === undefined && section.view === undefined" class="text-base text-ink-gray-5">
			Shows here once you save.
		</p>
		<div v-else-if="section.type === 'browse'" class="grid grid-cols-[repeat(auto-fill,minmax(12rem,1fr))] gap-3">
			<RouterLink
				v-for="kind in artifactKinds"
				:key="kind.kind"
				:to="`/home/${kind.kind}`"
				class="flex items-center gap-3 rounded-6 border border-outline-gray-2 p-3 text-base font-medium text-ink-gray-8 transition-colors hover:border-outline-gray-3 hover:bg-surface-gray-1"
			>
				<span :class="kind.icon" class="size-4 text-ink-gray-6" />
				{{ kind.title }}
			</RouterLink>
		</div>

		<template v-else-if="section.type === 'embed'">
			<div v-if="section.view?.view" class="h-[520px] overflow-hidden rounded-8 border border-outline-gray-2">
				<iframe :src="section.view.view" :title="section.view.title" class="size-full border-0" />
			</div>
			<p v-else class="text-base text-ink-gray-5">
				{{ section.view ? `This ${section.view.label.toLowerCase()} is not published yet.` : "You cannot open what this shows." }}
			</p>
		</template>

		<template v-else>
			<p v-if="!section.artifacts?.length" class="text-base text-ink-gray-5">{{ EMPTY[section.type] }}</p>
			<div v-else class="grid grid-cols-[repeat(auto-fill,minmax(16rem,1fr))] gap-3">
				<ArtifactCard v-for="artifact in section.artifacts" :key="`${artifact.doctype}/${artifact.name}`" :artifact="artifact" />
			</div>
		</template>
	</section>
</template>

<script setup lang="ts">
import { Button } from "frappe-ui"
import { computed } from "vue"
import { RouterLink } from "vue-router"

import { artifactKinds } from "../artifacts"
import ArtifactCard from "./ArtifactCard.vue"
import { type Section, sectionTitle, viewRoute } from "./home"

const props = defineProps<{ section: Section }>()
const title = computed(() => sectionTitle(props.section))

const EMPTY: Record<string, string> = {
	pinned: "Pin a view to keep it here.",
	recent: "Nothing has been built yet.",
	list: "Nothing here yet.",
	views: "Nothing here you can open.",
}
</script>
