<template>
	<div class="h-full overflow-y-auto bg-surface-base">
		<div v-if="loading" class="flex h-full items-center justify-center">
			<LoadingIndicator class="size-5 text-ink-gray-4" />
		</div>

		<div v-else-if="empty" class="flex h-full items-center justify-center px-6">
			<div class="flex w-full max-w-xl flex-col items-center text-center">
				<span class="grid size-10 place-items-center rounded-full bg-surface-gray-2">
					<span class="lucide-bot size-5 text-ink-gray-6" />
				</span>
				<h1 class="mt-4 text-2xl font-semibold text-ink-gray-9">Put agents to work</h1>
				<p class="mt-2 max-w-md text-p-base text-ink-gray-6">
					Tell the assistant what a helper should do and when: on a new record, every morning, or when someone asks. Its agents and automations show here.
				</p>
				<AskForm v-model="prompt" class="mt-6 w-full" :rows="3" placeholder="Score each new proposal from 1 to 10 and tag it" @submit="start" />
				<div class="mt-3 flex flex-wrap justify-center gap-1.5">
					<Button v-for="idea in IDEAS" :key="idea" size="sm" variant="subtle" :label="idea" @click="prompt = idea" />
				</div>
			</div>
		</div>

		<div v-else class="mx-auto flex w-full max-w-3xl flex-col gap-8 px-6 py-10">
			<div>
				<h1 class="text-xl font-semibold text-ink-gray-9">Agents</h1>
				<p class="mt-1 text-sm text-ink-gray-5">{{ summary }}</p>
				<AskForm v-model="prompt" class="mt-5" :rows="1" placeholder="Ask for an agent or an automation…" @submit="start" />
			</div>

			<section v-if="automations.length">
				<h2 class="mb-2 text-sm font-medium text-ink-gray-6">Automations</h2>
				<ul class="divide-y divide-outline-gray-1 rounded-6 border border-outline-gray-2">
					<li v-for="flow in automations" :key="flow.name">
						<RouterLink
							:to="{ name: 'agents-automation', params: { automation: flow.name } }"
							class="flex items-center gap-3 px-4 py-3 hover:bg-surface-gray-1"
						>
							<span class="lucide-workflow size-4 shrink-0 text-ink-gray-5" />
							<div class="min-w-0 flex-1">
								<p class="truncate text-sm font-medium text-ink-gray-8">{{ flow.title }}</p>
								<p class="mt-0.5 truncate text-sm text-ink-gray-5">{{ flow.trigger }} · {{ flow.does }}</p>
							</div>
							<span v-if="flow.last_run" class="flex shrink-0 items-center gap-1.5 text-sm text-ink-gray-5" :title="flow.last_run.started_at">
								<span class="size-1.5 rounded-full" :class="STATUS_DOT[flow.last_run.status]" />
								{{ flow.last_run.status }} · {{ dayjs(flow.last_run.started_at).fromNow() }}
							</span>
							<span v-else class="shrink-0 text-sm text-ink-gray-4">Not run yet</span>
							<Badge :label="flow.enabled ? 'On' : 'Off'" :theme="flow.enabled ? 'green' : 'gray'" size="sm" />
						</RouterLink>
					</li>
				</ul>
			</section>

			<section v-if="agents.length">
				<h2 class="mb-2 text-sm font-medium text-ink-gray-6">Agents</h2>
				<ul class="divide-y divide-outline-gray-1 rounded-6 border border-outline-gray-2">
					<li v-for="agent in agents" :key="agent.name">
						<RouterLink
							:to="{ name: 'agents-agent', params: { agent: agent.name } }"
							class="flex items-center gap-3 px-4 py-3 hover:bg-surface-gray-1"
						>
							<span class="lucide-bot size-4 shrink-0 text-ink-gray-5" />
							<div class="min-w-0 flex-1">
								<p class="truncate text-sm font-medium text-ink-gray-8">{{ agent.title }}</p>
								<p class="mt-0.5 truncate text-sm text-ink-gray-5">{{ agent.description || "No description" }}</p>
							</div>
							<span class="shrink-0 text-sm text-ink-gray-5">
								{{ agent.model }} · {{ agent.tools }} tool{{ agent.tools === 1 ? "" : "s" }}
							</span>
							<Badge v-if="!agent.enabled" label="Off" theme="gray" size="sm" />
						</RouterLink>
					</li>
				</ul>
			</section>
		</div>
	</div>
</template>

<script setup lang="ts">
import { onListUpdate } from "@shell/realtime"
import { useDebounceFn } from "@vueuse/core"
import { Badge, Button, LoadingIndicator, dayjs } from "frappe-ui"
import { computed, onBeforeUnmount, onMounted, ref } from "vue"
import { useRouter } from "vue-router"

import { type AgentRow, type AutomationRow, STATUS_DOT, getHome } from "../api"
import AskForm from "../components/AskForm.vue"

const IDEAS = ["Score and tag each new proposal", "Email me a digest every morning", "Answer attendee questions from the schedule"]

const router = useRouter()
const agents = ref<AgentRow[]>([])
const automations = ref<AutomationRow[]>([])
const loading = ref(true)
const empty = computed(() => !agents.value.length && !automations.value.length)

async function load() {
	const home = await getHome()
	agents.value = home.agents
	automations.value = home.automations
	loading.value = false
}
load()
const reload = useDebounceFn(load, 500)
const stops = ["Flow Agent", "Automation Flow", "Automation Run"].map((doctype) => onListUpdate(doctype, reload))
onBeforeUnmount(() => stops.forEach((stop) => stop()))

const plural = (count: number, word: string) => `${count} ${word}${count === 1 ? "" : "s"}`
const summary = computed(() =>
	[plural(automations.value.length, "automation"), plural(agents.value.length, "agent")].filter((part) => !part.startsWith("0 ")).join(" · ")
)

const prompt = ref("")
function start() {
	const text = prompt.value.trim()
	if (text) router.push({ name: "studio-chat", params: { session: "new" }, query: { prompt: text } })
}

onMounted(() => (document.title = "Agents"))
</script>
