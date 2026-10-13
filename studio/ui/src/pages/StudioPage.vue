<template>
	<AppPreview ref="preview" :appID="route.params.appID as string" :pageID="route.params.pageID as string" />
	<!-- the shell's contract has no place for a layer's own bar controls yet; they join its artifact bar -->
	<Teleport v-if="active" defer :to="ARTIFACT_BAR">
		<StudioToolbar />
	</Teleport>
</template>

<script setup lang="ts">
import { onActivated, onDeactivated, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import { usePageMeta } from "frappe-ui"

import StudioToolbar from "@ui/components/StudioToolbar.vue"
import AppPreview from "@ui/components/AppPreview.vue"
import useStudioStore from "@ui/stores/studioStore"

const ARTIFACT_BAR = 'section[data-layer="shell"] > .h-11 > .flex-1'

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

// the bar is drawn afresh when the page comes back from the keep-alive cache
const active = ref(true)
onActivated(() => {
	active.value = true
	preview.value?.loadPage(route.params.appID as string, route.params.pageID as string)
})

onDeactivated(() => {
	active.value = false
	store.selectedPage = null
	store.activePage = null
})

usePageMeta(() => ({ title: store.activePage?.page_title || store.activeApp?.app_title || "Apps" }))
</script>
