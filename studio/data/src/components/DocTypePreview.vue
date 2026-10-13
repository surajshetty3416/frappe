<template>
	<div ref="root" class="flex h-full flex-col bg-surface-base">
		<div v-if="doctype.error" class="flex flex-1 flex-col items-center justify-center px-6 text-center">
			<span class="lucide-triangle-alert size-5 text-ink-gray-4" />
			<p class="mt-3 text-base font-medium text-ink-gray-8">This DocType could not open</p>
			<p class="mt-1 max-w-sm text-p-sm text-ink-gray-5">{{ doctype.error }}</p>
		</div>
		<div v-else-if="!doctype.doc || doctype.doc.name !== name" class="flex flex-col gap-3 p-4">
			<Skeleton v-for="i in 6" :key="i" class="h-8 w-full rounded-4" />
		</div>
		<template v-else>
			<RecordsView v-if="view === 'records'" :key="`records-${name}`" class="min-h-0 flex-1" />
			<FormView v-else-if="view === 'form'" :key="`form-${name}`" class="min-h-0 flex-1" />
			<FieldsView v-else-if="view === 'fields'" class="min-h-0 flex-1" />
			<PermissionsView v-else class="min-h-0 flex-1" />
		</template>

		<DemoDataDialog />
	</div>
</template>

<script setup lang="ts">
import { editorMode } from "@shell/editor"
import { Skeleton } from "frappe-ui"
import { computed, onBeforeUnmount, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"

import { VIEW_MODES, doctype, open, preview, view } from "../doctype"
import { loadDoctypeNames } from "../names"
import DemoDataDialog from "./DemoDataDialog.vue"
import FieldsView from "./FieldsView.vue"
import FormView from "./FormView.vue"
import PermissionsView from "./PermissionsView.vue"
import RecordsView from "./RecordsView.vue"

const route = useRoute()
const router = useRouter()
preview.router = router

const root = ref<HTMLElement | null>(null)
watch(root, (element) => (preview.host = element))
onBeforeUnmount(() => (preview.host = null))

const name = computed(() => String(route.params.doctype ?? ""))
watch(
	name,
	(value) => {
		if (!value) return
		document.title = value
		if (value !== doctype.doc?.name) open(value)
	},
	{ immediate: true }
)
loadDoctypeNames()

// each view opens in its first mode
watch(view, (value) => (editorMode.value = VIEW_MODES[value][0]), { immediate: true })
</script>
