<template>
	<Dialog v-model:open="open" bare position="top" size="lg">
		<div data-layer="shell" data-home-shell class="flex flex-col">
			<div class="border-b border-outline-gray-1 p-2">
				<TextInput ref="input" v-model="query" variant="ghost" size="md" placeholder="Find a Space">
					<template #prefix><span class="lucide-search size-4 text-ink-gray-5" /></template>
				</TextInput>
			</div>
			<div class="max-h-[60vh] overflow-y-auto p-2">
				<p v-if="!matches.length" class="px-2 py-6 text-center text-sm text-ink-gray-5">No Space matches.</p>
				<div
					v-for="space in matches"
					:key="space.name"
					class="flex items-center gap-3 rounded-2 px-2 py-2 hover:bg-surface-gray-1"
				>
					<span :class="spaceIcon(space.icon)" class="size-4 shrink-0 text-ink-gray-6" />
					<RouterLink :to="`/home/s/${encodeURIComponent(space.name)}`" class="min-w-0 flex-1" @click="open = false">
						<p class="truncate text-sm font-medium text-ink-gray-8">{{ space.title }}</p>
						<p class="truncate text-sm text-ink-gray-5">{{ space.description || `${space.members} ${space.members === 1 ? "member" : "members"}` }}</p>
					</RouterLink>
					<Button v-if="joined.has(space.name)" size="sm" variant="ghost" label="Joined" disabled />
					<Button v-else size="sm" label="Join" :loading="joining === space.name" @click="join(space.name)" />
				</div>
			</div>
		</div>
	</Dialog>
</template>

<script setup lang="ts">
import { Button, Dialog, TextInput } from "frappe-ui"
import { computed, nextTick, ref, watch } from "vue"
import { RouterLink } from "vue-router"

import { joinSpace, loadSpaces, spaceIcon, spaces } from "./home"

// every Space the person can see, theirs first, to open or join
const open = defineModel<boolean>("open", { required: true })
const query = ref("")
const input = ref<{ focus: () => void } | null>(null)

watch(open, (opened) => {
	if (!opened) return
	query.value = ""
	loadSpaces()
	nextTick(() => input.value?.focus())
})

const joined = computed(() => new Set(spaces.value?.mine.map((space) => space.name)))
const matches = computed(() => {
	const words = query.value.trim().toLowerCase().split(/\s+/).filter(Boolean)
	return [...(spaces.value?.mine ?? []), ...(spaces.value?.others ?? [])].filter((space) =>
		words.every((word) => `${space.title} ${space.description ?? ""}`.toLowerCase().includes(word))
	)
})

const joining = ref<string | null>(null)
async function join(space: string) {
	joining.value = space
	try {
		await joinSpace(space)
	} finally {
		joining.value = null
	}
}
</script>
