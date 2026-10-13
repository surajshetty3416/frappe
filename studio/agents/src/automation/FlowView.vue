<template>
	<div class="overflow-y-auto bg-surface-gray-1 px-6 py-8">
		<ol class="mx-auto flex max-w-lg flex-col items-stretch">
			<li class="rounded-6 border border-outline-gray-2 bg-surface-base px-4 py-3">
				<p class="flex items-center gap-2 text-sm text-ink-gray-5"><span class="lucide-zap size-4" />Trigger</p>
				<p class="mt-1 text-base font-medium text-ink-gray-8">{{ flow.trigger }}</p>
			</li>

			<template v-if="flow.conditions.length || flow.condition">
				<li class="mx-auto h-6 border-l border-outline-gray-2" aria-hidden="true" />
				<li class="rounded-6 border border-outline-gray-2 bg-surface-base px-4 py-3">
					<p class="flex items-center gap-2 text-sm text-ink-gray-5"><span class="lucide-filter size-4" />Only when</p>
					<p v-if="flow.conditions.length" class="mt-1 text-sm text-ink-gray-8">{{ flow.conditions.join(" ") }}</p>
					<code v-if="flow.condition" class="mt-2 block whitespace-pre-wrap rounded-4 bg-surface-gray-2 px-2 py-1.5 font-mono text-sm text-ink-gray-7">{{ flow.condition }}</code>
				</li>
			</template>

			<template v-for="step in flow.steps" :key="step.idx">
				<li class="mx-auto h-6 border-l border-outline-gray-2" aria-hidden="true" />
				<li class="rounded-6 border border-outline-gray-2 bg-surface-base px-4 py-3" :class="step.parent_step ? 'ml-8' : ''">
					<p class="flex items-center gap-2 text-sm text-ink-gray-5">
						<span :class="iconOf(step)" class="size-4" />
						<span v-if="step.branch">{{ step.branch === "If" ? "Then" : "Otherwise" }} ·</span>
						{{ step.label }}
					</p>
					<template v-if="step.action_type === 'RunAgent'">
						<RouterLink
							v-if="step.agent"
							:to="{ name: 'agents-agent', params: { agent: step.agent }, query: route.query.chat ? { chat: route.query.chat } : {} }"
							class="mt-1 inline-flex items-center gap-1.5 text-base font-medium text-ink-gray-8 hover:underline"
						>
							{{ step.agent_title || step.agent }}
							<span class="lucide-arrow-up-right size-4 text-ink-gray-5" />
						</RouterLink>
						<p v-if="step.prompt?.length" class="mt-2 whitespace-pre-wrap rounded-4 bg-surface-gray-1 px-3 py-2 text-sm leading-6 text-ink-gray-7">
							<template v-for="(part, i) in step.prompt" :key="i"><span v-if="part.field" :class="CHIP">{{ part.field }}</span><template v-else>{{ part.text }}</template></template>
						</p>
					</template>
					<code v-else-if="step.detail" class="mt-2 block whitespace-pre-wrap rounded-4 bg-surface-gray-2 px-2 py-1.5 font-mono text-sm text-ink-gray-7">{{ step.detail }}</code>
					<dl v-if="step.params?.length" class="mt-2 flex flex-col gap-1">
						<div v-for="param in step.params" :key="param.label" class="flex gap-3 text-sm">
							<dt class="w-28 shrink-0 text-ink-gray-5">{{ param.label }}</dt>
							<dd class="min-w-0 break-words text-ink-gray-8">
								<template v-for="(part, i) in partsOf(param)" :key="i"><span v-if="part.field" :class="CHIP">{{ part.field }}</span><template v-else>{{ part.text }}</template></template>
							</dd>
						</div>
					</dl>
				</li>
			</template>

			<template v-if="!flow.steps.length">
				<li class="mx-auto h-6 border-l border-outline-gray-2" aria-hidden="true" />
				<li class="rounded-6 border border-dashed border-outline-gray-3 px-4 py-3 text-center text-sm text-ink-gray-5">No steps yet. Ask the chat to add one.</li>
			</template>
		</ol>
	</div>
</template>

<script setup lang="ts">
import { useRoute } from "vue-router"

import type { Flow, StepCard } from "../api"

defineProps<{ flow: Flow }>()
const route = useRoute()

// a value the run fills in from the record
const CHIP = "rounded-4 bg-surface-gray-3 px-0.5 py-0.5 text-ink-gray-8"
type Part = { text?: string; field?: string }
const partsOf = (param: { value?: string; parts?: Part[] }): Part[] => param.parts ?? [{ text: param.value }]
const ICONS: Record<string, string> = { Wait: "lucide-clock", WaitForEvent: "lucide-hourglass", If: "lucide-git-branch" }
const iconOf = (step: StepCard) => (step.action_type === "RunAgent" ? "lucide-bot" : ICONS[step.kind] ?? "lucide-square-play")
</script>
