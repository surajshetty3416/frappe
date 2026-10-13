<template>
	<div v-if="failedDocument" class="flex h-screen w-full items-center justify-center bg-surface-white p-4">
		<div class="flex flex-col items-center gap-3 text-center">
			<div class="text-base font-medium text-ink-gray-8">{{ failedDocument }}</div>
			<Button route="/" label="Back" icon-left="lucide-arrow-left" />
		</div>
	</div>
	<AppComponent v-else :block="root" />
</template>

<script setup lang="ts">
import { computed, provide, onUnmounted } from "vue"
import { Button, usePageMeta } from "frappe-ui"

import { useLoadedPage } from "@ui/page/pageLoader"
import { onPageScriptHotUpdate } from "@ui/data/studioPageScripts"
import AppComponent from "@ui/components/AppComponent.vue"

import useAppStore from "@ui/stores/appStore"
import useComponentStore from "@ui/stores/componentStore"
import { pageScopeKey } from "@ui/stores/codeStore"

const { page, scope, root } = useLoadedPage()

provide(pageScopeKey, scope)
onUnmounted(() => scope.teardownPage())
onUnmounted(onPageScriptHotUpdate((name, setup) => scope.applyPageScriptHotUpdate(name, setup)))

useAppStore().activePage = page
useComponentStore().setComponents(page.components || [])
usePageMeta(() => ({ title: page.page_title }))

// a page bound to one record has nothing to show without it, so the record's fetch error replaces the page
const failedDocument = computed(() => {
	for (const resource of Object.values(scope.resources) as any[]) {
		const error = resource?.get?.error
		if (!resource?.doctype || !error) continue
		const record = `${resource.doctype} ${resource.name}`
		return error.exc_type === "DoesNotExistError" ? `${record} not found` : `Could not load ${record}`
	}
	return null
})
</script>
