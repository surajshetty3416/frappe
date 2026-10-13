<template>
	<div class="flex">
		<div v-if="loading" class="flex flex-1 items-center justify-center">
			<LoadingIndicator class="size-4 text-ink-gray-5" />
		</div>
		<div v-else-if="!runs.length" class="flex flex-1 flex-col items-center justify-center px-6 text-center">
			<span class="lucide-history size-5 text-ink-gray-4" />
			<p class="mt-3 text-base font-medium text-ink-gray-8">No runs yet</p>
			<p class="mt-1 max-w-sm text-sm text-ink-gray-5">A run shows here when its trigger fires, or when you click Run now.</p>
		</div>
		<template v-else>
			<ul class="w-64 shrink-0 overflow-y-auto border-r border-outline-gray-1 p-2">
				<li v-for="run in runs" :key="run.name">
					<ItemListRow as="button" type="button" size="md" class="text-left hover:bg-surface-gray-2" :selected="run.name === selected" @click="selected = run.name">
						<template #prefix><span class="size-1.5 rounded-full" :class="STATUS_DOT[run.status]" /></template>
						<span class="block truncate text-sm">{{ run.status }}</span>
						<span class="block truncate text-sm text-ink-gray-5" :title="run.started_at ?? ''">{{ when(run.started_at) }}</span>
						<template #suffix><span class="text-sm text-ink-gray-5">{{ duration(run) }}</span></template>
					</ItemListRow>
				</li>
			</ul>

			<div class="min-w-0 flex-1 overflow-y-auto px-6 py-5">
				<div v-if="!detail" class="flex flex-col gap-3">
					<Skeleton v-for="i in 3" :key="i" class="h-12 w-full rounded-4" />
				</div>
				<template v-else>
					<div class="flex items-center gap-2">
						<span class="size-2 rounded-full" :class="STATUS_DOT[detail.status]" />
						<p class="text-base font-medium text-ink-gray-8">{{ detail.status }}</p>
					</div>
					<p class="mt-1 text-sm text-ink-gray-5">
						Started {{ detail.started_at ? dayjs(detail.started_at).format("D MMM, h:mm:ss a") : "—" }} · {{ duration(detail) }}
						<template v-if="detail.reference_name"> · on {{ detail.reference_doctype }} {{ detail.reference_name }}</template>
					</p>
					<p v-if="detail.error_summary" class="mt-3 rounded-4 bg-surface-red-1 px-3 py-2 text-sm text-ink-red-7">{{ detail.error_summary }}</p>

					<ol class="mt-5 flex flex-col gap-3">
						<li v-for="step in detail.steps" :key="step.idx" class="rounded-6 border border-outline-gray-2 px-4 py-3">
							<div class="flex items-center gap-2 text-sm">
								<span :class="step.action_type === 'RunAgent' ? 'lucide-bot' : 'lucide-square-play'" class="size-4 text-ink-gray-5" />
								<span class="min-w-0 flex-1 truncate font-medium text-ink-gray-8">{{ step.label }}<template v-if="step.agent"> · {{ step.agent }}</template></span>
								<span class="size-1.5 rounded-full" :class="STATUS_DOT[step.status]" />
								<span class="text-ink-gray-5">{{ step.status }} · {{ ms(step.duration_ms) }}</span>
							</div>
							<template v-if="step.agent_run">
								<p v-if="step.agent_run.output" class="mt-2 whitespace-pre-wrap text-sm text-ink-gray-8">{{ step.agent_run.output }}</p>
								<p v-else-if="step.agent_run.error" class="mt-2 text-sm text-ink-red-7">{{ step.agent_run.error }}</p>
								<p v-else class="mt-2 flex items-center gap-2 text-sm text-ink-gray-5">
									<LoadingIndicator v-if="step.agent_run.status === 'Running'" class="size-3.5" />
									The agent is {{ step.agent_run.status.toLowerCase() }}.
								</p>
								<RouterLink
									:to="{ name: 'studio-chat', params: { session: step.agent_run.session } }"
									class="mt-2 inline-flex items-center gap-1 text-sm text-ink-gray-6 hover:text-ink-gray-8 hover:underline"
								>
									Open its session <span class="lucide-arrow-up-right size-3.5" />
								</RouterLink>
							</template>
							<p v-else-if="step.message || step.detail" class="mt-2 whitespace-pre-wrap text-sm text-ink-gray-6">{{ step.message || step.detail }}</p>
						</li>
					</ol>
				</template>
			</div>
		</template>
	</div>
</template>

<script setup lang="ts">
import { ItemListRow, LoadingIndicator, Skeleton, dayjs } from "frappe-ui"
import { onBeforeUnmount, ref, watch } from "vue"

import { type Run, type RunRow, STATUS_DOT, getRun, getRuns } from "../api"

const props = defineProps<{ automation: string }>()

const runs = ref<RunRow[]>([])
const loading = ref(true)
const selected = ref<string | null>(null)
const detail = ref<Run | null>(null)

async function load() {
	runs.value = await getRuns(props.automation)
	loading.value = false
	if (!runs.value.some((run) => run.name === selected.value)) selected.value = runs.value[0]?.name ?? null
	else if (selected.value) loadDetail(selected.value)
}

async function loadDetail(name: string) {
	const run = await getRun(name)
	if (selected.value === name) detail.value = run
}

watch(selected, (name) => {
	detail.value = null
	if (name) loadDetail(name)
})

load()
// a run and its agent finish in the background
const timer = setInterval(load, 3000)
onBeforeUnmount(() => clearInterval(timer))

const when = (value: string | null) => (value ? dayjs(value).fromNow() : "Not started")
const ms = (value: number) => (value < 1000 ? `${value} ms` : `${(value / 1000).toFixed(1)} s`)
function duration(run: RunRow) {
	if (!run.started_at) return ""
	if (!run.ended_at) return "running"
	return ms(dayjs(run.ended_at).diff(dayjs(run.started_at)))
}
</script>
