<template>
	<div class="flex h-full flex-col bg-surface-base">
		<div class="flex h-11 shrink-0 items-center gap-2 border-b border-outline-gray-1 px-3">
			<TabButtons :options="VIEWS" :model-value="view" @update:model-value="setView" />
			<div class="flex-1" />
			<Switch v-if="flow" label="On" :model-value="Boolean(flow.doc.enabled)" @update:model-value="setEnabled" />
		</div>

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
	</div>
</template>

<script setup lang="ts">
import { Skeleton, Switch, TabButtons, toast } from "frappe-ui"
import { computed, watch } from "vue"
import { useRoute, useRouter } from "vue-router"

import { errorText, setValue } from "../api"
import FlowView from "./FlowView.vue"
import RunsView from "./RunsView.vue"
import { automation, open, preview } from "./state"

const VIEWS = [
	{ value: "flow", label: "Flow", iconLeft: "lucide-workflow" },
	{ value: "runs", label: "Runs", iconLeft: "lucide-history" },
]

const route = useRoute()
const router = useRouter()
preview.router = router

const name = computed(() => String(route.params.automation ?? ""))
const flow = computed(() => (automation.flow?.doc.name === name.value ? automation.flow : null))
const view = computed(() => (route.query.view === "runs" ? "runs" : "flow"))
const setView = (value: unknown) => router.replace({ query: { ...route.query, view: String(value) } })

watch(
	name,
	(value) => {
		if (!value) return
		if (value !== automation.flow?.doc.name) open(value)
	},
	{ immediate: true }
)
watch(flow, (value) => value && (document.title = value.doc.title))

async function setEnabled(enabled: boolean) {
	try {
		await setValue("Automation Flow", name.value, { enabled: enabled ? 1 : 0 })
	} catch (error) {
		toast.error(errorText(error))
	}
	await open(name.value)
}
</script>
