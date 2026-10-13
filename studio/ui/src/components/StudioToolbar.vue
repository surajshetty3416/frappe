<template>
	<div class="flex shrink-0 items-center gap-1">
		<div class="mx-1 h-4 w-px shrink-0 bg-surface-gray-3" />
		<PageSwitcher />
		<BreakpointToggle />
		<Button
			variant="ghost"
			icon="lucide-external-link"
			tooltip="Open"
			aria-label="Open"
			:disabled="!store.activePage"
			@click="store.openPage()"
		/>
	</div>
</template>

<script setup lang="ts">
import { Button } from "frappe-ui"
import useStudioStore from "@ui/stores/studioStore"
import PageSwitcher from "@ui/components/PageSwitcher.vue"
import BreakpointToggle from "@ui/components/BreakpointToggle.vue"

// the app's own controls on the shell's artifact bar
const store = useStudioStore()
</script>
