<template>
	<!-- the shell lets clicks through to its own selection UI only -->
	<div data-selection-ui class="flex h-9 shrink-0 items-center gap-1 border-b border-outline-gray-1 bg-surface-base px-2">
		<PageSwitcher />
		<div class="ml-auto flex items-center gap-1">
			<BreakpointToggle />
			<Button
				variant="ghost"
				icon="lucide-external-link"
				tooltip="Open page"
				aria-label="Open page"
				:disabled="!store.activePage"
				@click="store.openPage()"
			/>
		</div>
	</div>
</template>

<script setup lang="ts">
import { Button } from "frappe-ui"
import useStudioStore from "@ui/stores/studioStore"
import PageSwitcher from "@ui/components/PageSwitcher.vue"
import BreakpointToggle from "@ui/components/BreakpointToggle.vue"

// the page and the device the preview shows, over the preview
const store = useStudioStore()
</script>
