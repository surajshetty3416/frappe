<template>
	<div data-layer="shell" class="pointer-events-none absolute inset-x-0 bottom-5 z-10 flex justify-center px-6">
		<div class="pointer-events-auto w-full max-w-[640px]">
			<div
				v-if="focused && matches.length"
				class="mb-2 flex flex-col gap-0.5 rounded-3 border border-outline-gray-2 bg-surface-base p-1.5 shadow-xl"
			>
				<RouterLink
					v-for="(match, i) in matches"
					:key="`${match.doctype}/${match.name}`"
					:to="viewRoute(match)"
					class="flex items-center gap-2 rounded-2 px-2 py-1.5 text-base text-ink-gray-8"
					:class="i === picked ? 'bg-surface-gray-2' : 'hover:bg-surface-gray-1'"
					@mousedown.prevent
					@click="reset"
				>
					<span :class="artifactIcon(match)" class="size-4 shrink-0 text-ink-gray-5" />
					<span class="min-w-0 flex-1 truncate">{{ match.title }}</span>
					<span class="shrink-0 text-sm text-ink-gray-4">{{ match.label }}</span>
				</RouterLink>
				<p class="px-2 pt-1 text-xs text-ink-gray-4">↑↓ to pick a view · Enter to ask</p>
			</div>
			<form
				class="flex items-center gap-2 rounded-full border border-outline-gray-2 bg-surface-base py-1.5 pl-4 pr-1.5 shadow-xl"
				@submit.prevent="submit"
			>
				<span class="lucide-sparkles size-4 shrink-0 text-ink-gray-5" />
				<button
					v-if="openView && viewInChat"
					type="button"
					class="flex max-w-[180px] shrink-0 items-center gap-1 rounded-full bg-surface-gray-2 py-0.5 pl-2 pr-1 text-sm text-ink-gray-7"
					:title="`Asking about ${openView.title}`"
					@click="viewInChat = false"
				>
					<span class="truncate">{{ openView.title }}</span>
					<span class="lucide-x size-3 shrink-0 text-ink-gray-5" />
				</button>
				<input
					ref="input"
					v-model="text"
					class="min-w-0 flex-1 border-0 bg-transparent p-0 text-base text-ink-gray-8 placeholder:text-ink-gray-4 focus:outline-none focus:ring-0"
					:placeholder="openView && viewInChat ? 'Ask about this view…' : 'Search views, or ask anything…'"
					@focus="focused = true"
					@blur="focused = false"
					@keydown.down.prevent="move(1)"
					@keydown.up.prevent="move(-1)"
					@keydown.esc="input?.blur()"
				/>
				<span class="shrink-0 text-xs text-ink-gray-4">⌘K</span>
				<Button variant="solid" icon="lucide-arrow-up" :disabled="!text.trim()" type="submit" />
			</form>
		</div>
	</div>
</template>

<script setup lang="ts">
import { Button } from "frappe-ui"
import { computed, nextTick, ref, watch } from "vue"
import { RouterLink, useRouter } from "vue-router"

import { artifactIcon, artifactKinds } from "../artifacts"
import { type ProjectArtifact, getArtifacts } from "../projects"
import { ask, askFocus, openView, viewInChat, viewRoute } from "./home"

const router = useRouter()
const input = ref<HTMLInputElement | null>(null)
const text = ref("")
const focused = ref(false)
// the match the arrows picked; Enter opens it, or asks when none is picked
const picked = ref(-1)

const everything = ref<ProjectArtifact[]>([])
getArtifacts(
	artifactKinds.flatMap((kind) => kind.doctypes),
	null
)
	.then((list) => (everything.value = list))
	.catch(() => {})

const matches = computed(() => {
	const words = text.value.trim().toLowerCase().split(/\s+/).filter(Boolean)
	if (!words.length) return []
	return everything.value.filter((artifact) => words.every((word) => artifact.title.toLowerCase().includes(word))).slice(0, 6)
})
watch(matches, () => (picked.value = -1))

function move(step: number) {
	if (!matches.value.length) return
	picked.value = Math.max(-1, Math.min(matches.value.length - 1, picked.value + step))
}

function reset() {
	text.value = ""
	input.value?.blur()
}

function submit() {
	const match = matches.value[picked.value]
	if (match) router.push(viewRoute(match))
	else if (text.value.trim()) ask(text.value.trim())
	reset()
}

watch(askFocus, () => nextTick(() => input.value?.focus()))
</script>
