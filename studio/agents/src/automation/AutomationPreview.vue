<template>
	<div class="flex h-full flex-col bg-surface-base">
		<div v-if="automation.error" class="flex flex-1 flex-col items-center justify-center px-6 text-center">
			<span class="lucide-triangle-alert size-5 text-ink-gray-4" />
			<p class="mt-3 text-base font-medium text-ink-gray-8">This automation could not open</p>
			<p class="mt-1 max-w-sm text-p-sm text-ink-gray-5">{{ automation.error }}</p>
		</div>
		<div v-else-if="!flow" class="flex flex-col gap-3 p-4">
			<Skeleton v-for="i in 4" :key="i" class="h-12 w-full rounded-4" />
		</div>
		<FlowView v-else-if="view === 'flow'" :flow="flow" class="min-h-0 flex-1" />
		<RunsView v-else :key="name" :automation="name" class="min-h-0 flex-1" />
		<RunNowDialog v-if="flow?.doc.document_type" :key="name" :doctype="flow.doc.document_type" />
	</div>
</template>

<script setup lang="ts">
import { Skeleton } from "frappe-ui"
import { computed, watch } from "vue"
import { useRoute, useRouter } from "vue-router"

import FlowView from "./FlowView.vue"
import RunNowDialog from "./RunNowDialog.vue"
import RunsView from "./RunsView.vue"
import { automation, open, preview } from "./state"

const route = useRoute()
preview.router = useRouter()

const name = computed(() => String(route.params.automation ?? ""))
const flow = computed(() => (automation.flow?.doc.name === name.value ? automation.flow : null))
const view = computed(() => (route.query.view === "runs" ? "runs" : "flow"))

watch(
	name,
	(value) => {
		if (!value) return
		automation.choosing = false
		if (value !== automation.flow?.doc.name) open(value)
	},
	{ immediate: true }
)
watch(flow, (value) => value && (document.title = value.doc.title))
</script>
