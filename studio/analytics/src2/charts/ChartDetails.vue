<script setup lang="ts">
import { FormControl } from 'frappe-ui'
import { __ } from '../translation'
import useChart from './chart'

// The chart's title and description in the shell's Details drawer. The chart saves itself.
const props = defineProps<{ name: string }>()
const chart = useChart(props.name)
</script>

<template>
	<div class="flex flex-col gap-4 p-4">
		<FormControl v-model="chart.doc.title" :label="__('Title')" />
		<FormControl
			type="textarea"
			:model-value="chart.doc.description ?? ''"
			:label="__('Description')"
			@update:model-value="(value: string) => (chart.doc.description = value)"
		/>
	</div>
</template>
