<template>
	<!-- a closing menu returns focus to its button, and focus opens a tooltip; the tooltip stays quiet while the menu
	     is open and after it closes, until the pointer or focus leaves the button -->
	<TooltipProvider :disabled="open || quiet">
		<Dropdown v-model:open="open" :options="options" :align="align">
			<Button v-bind="$attrs" @pointerleave="quiet = false" @blur="quiet = false" />
		</Dropdown>
	</TooltipProvider>
</template>

<script setup>
import { ref, watch } from "vue"
import { Button, Dropdown, TooltipProvider } from "frappe-ui"

defineOptions({ inheritAttrs: false })
defineProps({
	options: { type: Array, required: true },
	align: { type: String, default: "start" },
})

const open = ref(false)
const quiet = ref(false)
watch(open, (isOpen) => !isOpen && (quiet.value = true))
</script>
