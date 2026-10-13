<template>
	<div class="flex h-full flex-col">
		<StudioToolbar />
		<AppPreview ref="preview" class="min-h-0 flex-1" :appID="route.params.appID as string" :pageID="route.params.pageID as string" />
	</div>
</template>

<script setup lang="ts">
import { onActivated, onDeactivated, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import { usePageMeta } from "frappe-ui"

import AppPreview from "@ui/components/AppPreview.vue"
import StudioToolbar from "@ui/components/StudioToolbar.vue"
import useStudioStore from "@ui/stores/studioStore"

const route = useRoute()
const router = useRouter()
const store = useStudioStore()
const preview = ref<InstanceType<typeof AppPreview> | null>(null)

watch(
	() => route.params.pageID,
	async (pageID) => {
		if (pageID !== "new") return
		const appID = route.params.appID as string
		const page = await store.createPage(appID)
		router.replace({ name: "StudioPage", params: { appID, pageID: page.name } })
	},
	{ immediate: true },
)

onActivated(() => {
	preview.value?.loadPage(route.params.appID as string, route.params.pageID as string)
})

onDeactivated(() => {
	store.selectedPage = null
	store.activePage = null
})

usePageMeta(() => ({ title: store.activePage?.page_title || store.activeApp?.app_title || "Apps" }))
</script>
