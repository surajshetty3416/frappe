<script setup lang="ts">
import { computed } from 'vue'
import Code from '../components/Code.vue'
import useDashboard from './dashboard'

// The dashboard's Code view: its layout as JSON, the tiles and where they sit.
const props = defineProps<{ name: string }>()

const dashboard = useDashboard(props.name)

const layout = computed(() => JSON.stringify(dashboard.doc.items, null, 2))
</script>

<template>
	<div class="flex h-full w-full overflow-hidden rounded-4 border">
		<Code :model-value="layout" language="javascript" read-only />
	</div>
</template>
