<template>
	<div class="flex min-w-0 flex-1 items-center gap-1">
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

// the page and the device the preview shows, on the shell's context row
const store = useStudioStore()
</script>
