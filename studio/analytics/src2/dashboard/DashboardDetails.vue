<script setup lang="ts">
import { FormControl, Switch } from 'frappe-ui'
import { __ } from '../translation'
import useDashboard from './dashboard'

// The dashboard's settings in the shell's Details drawer. The dashboard saves itself.
const props = defineProps<{ name: string }>()
const dashboard = useDashboard(props.name)
</script>

<template>
	<div class="flex flex-col gap-4 p-4">
		<FormControl v-model="dashboard.doc.title" :label="__('Title')" />
		<Switch
			:model-value="Boolean(dashboard.doc.vertical_compact_layout)"
			:label="__('Close gaps between tiles')"
			@update:model-value="(on: boolean) => (dashboard.doc.vertical_compact_layout = on)"
		/>
	</div>
</template>
