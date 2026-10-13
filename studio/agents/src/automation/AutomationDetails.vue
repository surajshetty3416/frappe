<template>
	<div v-if="automation.flow" class="p-4">
		<EnabledField
			doctype="Automation Flow"
			:name="automation.name"
			:enabled="Boolean(automation.flow.doc.enabled)"
			:reload="() => open(automation.name)"
		/>
	</div>
</template>

<script setup lang="ts">
import EnabledField from "../components/EnabledField.vue"
import { automation, open } from "./state"
</script>
