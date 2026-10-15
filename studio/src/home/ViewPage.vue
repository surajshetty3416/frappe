<template>
	<div data-layer="shell" class="flex h-full flex-col">
		<header class="flex h-12 shrink-0 items-center gap-2 border-b border-outline-gray-1 px-3">
			<nav class="flex min-w-0 flex-1 items-center gap-1.5 text-base">
				<RouterLink :to="`/home/${kind?.kind}`" class="shrink-0 text-ink-gray-5 hover:text-ink-gray-8">{{ kind?.title }}</RouterLink>
				<span class="shrink-0 text-ink-gray-4">/</span>
				<h1 class="min-w-0 truncate font-medium text-ink-gray-8">{{ view?.title ?? name }}</h1>
			</nav>
			<template v-if="view">
				<Button
					variant="ghost"
					:icon="view.pinned ? 'lucide-pin-off' : 'lucide-pin'"
					:tooltip="view.pinned ? 'Unpin' : 'Pin to home'"
					@click="togglePin"
				/>
				<Button variant="ghost" icon="lucide-info" tooltip="Details" @click="showDetails" />
				<Button v-if="view.can_write" variant="solid" icon-left="lucide-pencil" label="Edit" :route="view.route" />
			</template>
		</header>
		<div v-if="error" class="flex flex-1 items-center justify-center p-6 text-center text-base text-ink-gray-6">{{ error }}</div>
		<div v-else-if="!view" class="flex flex-1 items-center justify-center">
			<LoadingIndicator class="size-4 text-ink-gray-5" />
		</div>
		<iframe v-else-if="view.view" :key="view.view" :src="view.view" :title="view.title" class="min-h-0 w-full flex-1 border-0" />
		<div v-else class="flex flex-1 flex-col items-center justify-center gap-3 p-6 text-center">
			<p class="text-base text-ink-gray-6">This {{ view.label.toLowerCase() }} is not published yet.</p>
			<Button v-if="view.can_write" label="Edit in Studio" :route="view.route" />
		</div>
	</div>
</template>

<script setup lang="ts">
import { Button, LoadingIndicator } from "frappe-ui"
import { computed, ref, watch } from "vue"
import { RouterLink, useRoute } from "vue-router"

import { artifactKind } from "../artifacts"
import { getView, openView, pane, setPinned, viewInChat } from "./home"

const route = useRoute()
const kind = computed(() => artifactKind(route))
const name = computed(() => String(route.params.name))

const view = openView
const error = ref("")
watch(
	[kind, name],
	async ([shown, opened]) => {
		view.value = null
		error.value = ""
		viewInChat.value = true
		if (!shown) return
		try {
			const loaded = await getView(shown.doctypes[0], opened)
			if (name.value !== opened) return
			view.value = loaded
			document.title = loaded.title
		} catch {
			error.value = `This ${shown.title.toLowerCase()} could not be opened. It may have been deleted, or you may not have access to it.`
		}
	},
	{ immediate: true }
)

async function togglePin() {
	if (!view.value) return
	const pinned = !view.value.pinned
	view.value.pinned = pinned
	await setPinned(view.value, pinned)
}

function showDetails() {
	pane.value = pane.value.open && pane.value.tab === "details" ? { ...pane.value, open: false } : { open: true, tab: "details" }
}
</script>
