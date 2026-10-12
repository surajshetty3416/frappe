<template>
	<div class="h-full overflow-y-auto bg-surface-base">
		<div class="mx-auto flex w-full max-w-2xl flex-col px-6 pb-16 pt-[18vh]">
			<h1 class="text-3xl font-semibold text-ink-gray-9">What do you want to build?</h1>
			<p class="mt-2 text-p-base text-ink-gray-6">
				A website, a dashboard, an app, or any change to the data on this site.
			</p>

			<form class="mt-6 rounded-7 border border-outline-gray-2 bg-surface-white shadow-sm focus-within:border-outline-gray-3" @submit.prevent="start">
				<textarea
					ref="input"
					v-model="prompt"
					rows="3"
					class="block w-full resize-none border-0 bg-transparent px-4 pt-3.5 text-p-base text-ink-gray-8 placeholder-ink-gray-4 focus:ring-0"
					placeholder="A landing page for our bakery, with this week's specials from the Item list"
					@keydown.enter.exact.prevent="start"
				/>
				<div class="flex items-center justify-between px-3 pb-3">
					<div class="flex flex-wrap gap-1.5">
						<Button v-for="idea in ideas" :key="idea" size="sm" variant="subtle" :label="idea.trim()" @click="usePrompt(idea)" />
					</div>
					<Button variant="solid" icon="lucide-arrow-up" :disabled="!prompt.trim()" type="submit" tooltip="Start" />
				</div>
			</form>

			<Alert
				v-if="needsSetup"
				class="mt-4"
				theme="amber"
				title="Studio needs an AI model before it can answer."
				:primary-action="{ label: 'Set up a model', onClick: () => router.push('/studio/ai') }"
			/>

			<section class="mt-12">
				<h2 class="text-sm font-medium text-ink-gray-6">Recent</h2>
				<div v-if="history.loading && !history.data" class="mt-4">
					<LoadingIndicator class="size-4 text-ink-gray-5" />
				</div>
				<p v-else-if="!history.data?.length" class="mt-3 text-p-sm text-ink-gray-5">
					Your chats, and the websites, dashboards and apps they made, show up here.
				</p>
				<ul v-else class="mt-2 divide-y divide-outline-gray-1">
					<li v-for="chat in history.data" :key="chat.name">
						<router-link
							:to="{ name: 'studio-chat', params: { session: chat.name } }"
							class="flex items-center gap-3 rounded-4 px-2 py-2.5 hover:bg-surface-gray-1"
						>
							<span class="lucide-message-square size-4 shrink-0 text-ink-gray-5" />
							<span class="min-w-0 flex-1 truncate text-base text-ink-gray-8">{{ chat.title || "Untitled chat" }}</span>
							<span
								v-for="artifact in chat.artifacts.slice(0, 2)"
								:key="artifact.doctype + artifact.name"
								class="flex max-w-[12rem] items-center gap-1 rounded-3 bg-surface-gray-2 px-1.5 py-0.5 text-xs text-ink-gray-7"
							>
								<span :class="artifactIcon(artifact)" class="size-3 shrink-0" />
								<span class="truncate">{{ artifact.title }}</span>
							</span>
							<span class="w-20 shrink-0 text-right text-sm text-ink-gray-5">{{ dayjs(chat.modified).fromNow() }}</span>
						</router-link>
					</li>
				</ul>
			</section>
		</div>
	</div>
</template>

<script setup lang="ts">
import { Alert, Button, LoadingIndicator, createResource, dayjs } from "frappe-ui"
import { onMounted, ref } from "vue"
import { useRouter } from "vue-router"

import { type Chat, artifactIcon } from "../artifacts"

const router = useRouter()
const input = ref<HTMLTextAreaElement | null>(null)
const prompt = ref("")
const ideas = ["A website for ", "A dashboard of ", "An app to "]

const history = createResource<Chat[]>({ url: "frappe.ai.artifacts.get_history", params: { limit: 30 }, auto: true })
const needsSetup = !window.flow_boot?.models?.length

function usePrompt(idea: string) {
	prompt.value = idea
	input.value?.focus()
}

function start() {
	const text = prompt.value.trim()
	if (!text) return
	router.push({ name: "studio-chat", params: { session: "new" }, query: { prompt: text } })
}

onMounted(() => {
	document.title = "Studio"
	input.value?.focus()
})
</script>
