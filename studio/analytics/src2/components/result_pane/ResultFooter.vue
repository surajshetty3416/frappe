<script setup lang="ts">
import type { PaginationState } from '../../composables/usePagination'
import DataTableFooter from '../DataTableFooter.vue'

// The pane's bottom band: the result's status on the left, the pager on the right.
const props = defineProps<{
	/** absent until a run has returned columns */
	pagination?: PaginationState
}>()
</script>

<template>
	<DataTableFooter
		:pagination="props.pagination"
		@prev="props.pagination?.prev()"
		@next="props.pagination?.next()"
	>
		<template #left>
			<slot name="left" />
		</template>
	</DataTableFooter>
</template>
