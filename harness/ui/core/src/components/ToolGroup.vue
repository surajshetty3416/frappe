<template>
	<div class="flex flex-col">
		<template v-for="step in steps" :key="step.call ? step.call.id : step.id">
			<ThoughtStep v-if="step.thought" :id="step.id" :block="step.thought" :live="!sealed && !!step.live" />
			<ToolStep v-else :step="step" :live="!sealed && isLive(step)" />
		</template>
	</div>
</template>

<script setup>
import { computed } from "vue"

import ThoughtStep from "./ThoughtStep.vue"
import ToolStep from "./ToolStep.vue"

const props = defineProps({
	steps: { type: Array, required: true },
	// sealed = a text blob follows this group, or the run settled
	sealed: { type: Boolean, default: true },
})

const runningStep = computed(() => props.steps.find((s) => s.call && !s.result && !s.aborted) ?? null)
// a sub-agent's row runs on its child's clock: several can be live at once
const isLive = (step) => step === runningStep.value || (!!step.subagent?.running && !step.result)
</script>
