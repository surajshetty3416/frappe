<template>
	<div class="flex h-full w-full flex-col gap-2">
		<div v-if="tab !== 'Script'" class="flex items-center justify-between">
			<span class="text-sm text-ink-gray-5">JSON</span>
			<Button :loading="saving" label="Save" icon-left="lucide-check" @click="save" />
		</div>
		<PageScript v-if="tab === 'Script'" class="min-h-0 flex-1" />
		<div v-else class="relative min-h-0 flex-1 overflow-hidden rounded-4 border border-outline-gray-2">
			<Code
				:key="tab"
				v-model="source[tab]"
				language="json"
				height="100%"
				maxHeight="100%"
				:emitOnChange="true"
				valueMode="text"
				:borderless="true"
				@save="save"
			/>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue"
import { Button, toast } from "frappe-ui"
import Code from "@ui/components/Code.vue"
import PageScript from "@ui/components/PageScript.vue"
import useStudioStore from "@ui/stores/studioStore"
import useCanvasStore from "@ui/stores/canvasStore"
import { usePageScope } from "@ui/stores/codeStore"
import { studioPageResources } from "@ui/data/studioResources"
import { getBlockCopyWithoutParent, getBlockInstance, jsToJson } from "@ui/utils/serializer"
import type { Resource } from "@ui/types/Studio/StudioResource"

// One part of the open page as code, a tab of the shell's Code drawer: its component tree, its
// script or its data sources
const props = defineProps<{ part: "Page" | "Script" | "Data" }>()
const store = useStudioStore()
const canvasStore = useCanvasStore()
const pageScope = usePageScope()

const tab = computed(() => props.part)
const source = reactive({ Page: "", Data: "" })
const saving = ref(false)

function load() {
	const root = canvasStore.activeCanvas?.getRootBlock()
	source.Page = root ? jsToJson(getBlockCopyWithoutParent(root)) : ""
	source.Data = JSON.stringify(studioPageResources.data || [], null, 2)
}
watch([tab, () => store.activePage?.name], load, { immediate: true })

async function save() {
	saving.value = true
	try {
		if (tab.value === "Page") savePage()
		else await saveData()
		toast.success("Saved")
	} catch (error: any) {
		toast.error("Could not save", { description: error?.messages?.join(", ") || error?.message })
	} finally {
		saving.value = false
	}
}

// the canvas autosaves the new tree
function savePage() {
	canvasStore.activeCanvas?.setRootBlock(getBlockInstance(JSON.parse(source.Page)), false, false)
}

async function saveData() {
	const page = store.activePage
	if (!page) return
	const rows: Resource[] = JSON.parse(source.Data)
	const kept = new Set(rows.map((row) => row.resource_id).filter(Boolean))
	const removed = (studioPageResources.data as Resource[]).filter((row) => !kept.has(row.resource_id))
	for (const { resource_id, ...values } of rows) {
		if (resource_id) await studioPageResources.setValue.submit({ name: resource_id, ...values })
		else
			await studioPageResources.insert.submit({
				...values,
				parent: page.name,
				parenttype: "Studio Page",
				parentfield: "resources",
			})
	}
	for (const row of removed) await studioPageResources.delete.submit(row.resource_id)
	await pageScope.setPageResources(page, true)
	await store.refreshActivePageModified()
	load()
}
</script>
