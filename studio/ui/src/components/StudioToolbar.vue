<template>
	<!-- the layer's styles reach only inside data-layer="ui"; order keeps the shell's status beside its title -->
	<div data-layer="ui" class="flex min-w-0 flex-1 items-center gap-2" style="order: 1">
		<div class="h-4 w-px shrink-0 bg-surface-gray-3" />
		<PageSwitcher />
		<BreakpointToggle />
		<Button
			class="ml-auto"
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

// the app's own controls on the shell's artifact bar, after the title and status
const store = useStudioStore()
</script>
