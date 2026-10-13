<template>
	<div class="flex h-12 items-center gap-2 border-b border-outline-gray-2 bg-surface-base px-3">
		<PageSwitcher />
		<BreakpointToggle />
		<div class="ml-auto flex items-center gap-2">
			<Button
				variant="subtle"
				icon="lucide-external-link"
				tooltip="Open"
				aria-label="Open"
				:disabled="!store.activePage"
				@click="store.openPage()"
			/>
			<PublishButton />
		</div>
	</div>
</template>

<script setup lang="ts">
import { Button } from "frappe-ui"
import useStudioStore from "@ui/stores/studioStore"
import PageSwitcher from "@ui/components/PageSwitcher.vue"
import BreakpointToggle from "@ui/components/BreakpointToggle.vue"
import PublishButton from "@ui/components/PublishButton.vue"

const store = useStudioStore()
</script>
