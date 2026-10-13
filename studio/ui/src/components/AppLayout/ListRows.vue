<template>
	<ListRows v-if="items?.length" v-bind="$attrs" :items="items">
		<template #default="row">
			<slot v-bind="row" />
		</template>
	</ListRows>
	<div v-else v-bind="$attrs" data-slot="list-row" role="row" class="text-sm text-ink-gray-5">
		<div class="col-span-full flex items-center">{{ emptyStateMessage || "No records" }}</div>
	</div>
</template>

<script setup lang="ts">
import { ListRows } from "frappe-ui/list"

defineOptions({ inheritAttrs: false })
defineProps<{ items?: unknown[]; emptyStateMessage?: string }>()
</script>
