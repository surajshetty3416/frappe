<template>
	<div class="w-48 min-w-28 shrink" :title="options.find((option) => option.value === state.record)?.label">
		<Combobox
			class="w-full"
			trigger="button"
			:model-value="state.record"
			:options="options"
			:placeholder="`Choose a ${state.target ?? 'record'}`"
			@update:model-value="(value) => value && pick(String(value))"
		/>
	</div>
</template>

<script setup lang="ts">
import { Combobox } from "frappe-ui"
import { computed } from "vue"
import { useRoute, useRouter } from "vue-router"

import type { OutputState } from "./outputEditor"

// the record the output renders against
const props = defineProps<{ state: OutputState }>()
const route = useRoute()
const router = useRouter()

const options = computed(() =>
	props.state.records.map((record) => ({
		label: record.title || record.name,
		value: record.name,
		description: record.title && record.title !== record.name ? record.name : undefined,
	})),
)
// the record is in the path: a link to an artifact keeps its path, and the chat adds its own query
const pick = (record: string) => router.replace({ params: { ...route.params, record }, query: route.query })
</script>
