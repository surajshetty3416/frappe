<template>
	<Button variant="solid" :loading="store.publishingApp" :disabled="!store.activeApp" @click="store.publishApp()">
		Publish
	</Button>
</template>

<script setup lang="ts">
import { Button } from "frappe-ui"
import useStudioStore from "@ui/stores/studioStore"

const store = useStudioStore()
</script>
