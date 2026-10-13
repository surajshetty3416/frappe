<template>
	<div class="relative h-full w-full overflow-hidden bg-surface-gray-2">
		<StudioCanvas
			v-if="store.pageBlocks[0]"
			ref="pageCanvas"
			class="canvas-container absolute inset-0 flex justify-center overflow-hidden"
			:componentTree="store.pageBlocks[0]"
		/>
	</div>
</template>

<script setup lang="ts">
import { ref, watch, watchEffect } from "vue"
import { useDebounceFn } from "@vueuse/core"
import { toast } from "frappe-ui"

import StudioCanvas from "@ui/components/StudioCanvas.vue"
import useStudioStore from "@ui/stores/studioStore"
import useCanvasStore from "@ui/stores/canvasStore"
import { useStudioEvents } from "@ui/utils/useStudioEvents"

// One app page rendered with its data, editable by selection. The shell mounts this as the preview.
const props = defineProps<{ appID: string; pageID: string }>()

const store = useStudioStore()
const canvasStore = useCanvasStore()
useStudioEvents()

const pageCanvas = ref<InstanceType<typeof StudioCanvas> | null>(null)
watchEffect(() => (canvasStore.activeCanvas = pageCanvas.value))

const debouncedPageSave = useDebounceFn(store.savePage, 300)
watch(
	() => pageCanvas.value?.rootComponent,
	() => {
		if (
			store.selectedPage &&
			!pageCanvas.value?.canvasProps?.settingCanvas &&
			!store.settingPage &&
			!store.savingPage &&
			!store.pageConflict
		) {
			store.savingPage = true
			debouncedPageSave()
		}
	},
	{ deep: true },
)

let loadingPageID: string | null = null
async function loadPage(appID: string, pageID: string) {
	if (!pageID || pageID === "new" || pageID === store.selectedPage || loadingPageID === pageID) return
	loadingPageID = pageID
	try {
		await store.setApp(appID)
		await store.setPage(pageID)
	} catch (error) {
		console.error(`Failed to load page ${pageID}`, error)
		toast.error("Failed to load the page")
	} finally {
		loadingPageID = null
	}
}

watch(() => [props.appID, props.pageID], () => loadPage(props.appID, props.pageID), { immediate: true })

defineExpose({ loadPage })
</script>
