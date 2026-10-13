<template>
	<div v-if="page" class="flex flex-col gap-4 p-4">
		<TextInput label="Title" :model-value="page.page_title" @change="set('page_title', value($event))" />
		<TextInput label="Address" :model-value="page.route" @change="set('route', value($event).replace(/^\/+/, ''))">
			<template #prefix><span class="text-sm text-ink-gray-5">/</span></template>
		</TextInput>
		<Switch
			label="Requires sign-in"
			:model-value="Boolean(page.authenticated_access)"
			@update:model-value="(on: boolean) => set('authenticated_access', on ? 1 : 0)"
		/>
		<Textarea
			label="Description"
			class="[&_textarea]:resize-none"
			:rows="3"
			placeholder="What search results and link previews show"
			:model-value="page.meta_description || ''"
			@change="set('meta_description', value($event))"
		/>
		<TextInput
			label="Social image"
			placeholder="/files/cover.png"
			:model-value="page.meta_image || ''"
			@change="set('meta_image', value($event))"
		/>
		<Switch
			label="Hide from search engines"
			:model-value="Boolean(page.disable_indexing)"
			@update:model-value="(on: boolean) => set('disable_indexing', on ? 1 : 0)"
		/>
	</div>
</template>

<script setup lang="ts">
import usePageStore from "@web/stores/pageStore"
import type { BuilderPage } from "@web/types/doctypes"
import { Switch, TextInput, Textarea, toast } from "frappe-ui"
import { computed } from "vue"

const pageStore = usePageStore()
const page = computed(() => pageStore.activePage)

const value = (event: Event) => (event.target as HTMLInputElement).value.trim()

// one save at a time: two at once on the same page fail as a conflict
let saving: Promise<unknown> = Promise.resolve()
function set(field: keyof BuilderPage, next: string | number) {
	saving = saving.then(async () => {
		const current = page.value
		if (!current || (current[field] ?? "") === next) return
		try {
			await pageStore.updateActivePage(field, next)
		} catch (error) {
			toast.error((error as { messages?: string[] }).messages?.join(", ") || "Could not save")
			pageStore.activePage = await pageStore.fetchActivePage(current.name)
		}
	})
}
</script>
