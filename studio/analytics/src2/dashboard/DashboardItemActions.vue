<script setup lang="ts">
import { Button } from 'frappe-ui'
import { Trash2 } from 'lucide-vue-next'
import { inject } from 'vue'
import { Dashboard } from './dashboard'
import { __ } from '../translation'

// What a selected tile offers until the editor shell's selection toolbar does.
const props = defineProps<{ itemIndex: number }>()

const dashboard = inject('dashboard') as Dashboard
</script>
<!-- A button, and not a div that listens: the grid lets a press through when it
	lands on a native control, so anything else starts a drag. -->
<template>
	<div class="flex w-fit rounded-4 bg-surface-gray-9 shadow-sm">
		<Button
			variant="ghost"
			:label="__('Delete')"
			class="!text-ink-gray-1 hover:!bg-surface-gray-8"
			@click="dashboard.removeItem(props.itemIndex)"
		>
			<template #icon>
				<Trash2 class="h-3.5 w-3.5" />
			</template>
		</Button>
	</div>
</template>
