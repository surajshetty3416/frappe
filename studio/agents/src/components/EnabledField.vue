<template>
	<Switch label="On" :model-value="enabled" @update:model-value="set" />
</template>

<script setup lang="ts">
import { Switch, toast } from "frappe-ui"

import { errorText, setValue } from "../api"

const props = defineProps<{ doctype: string; name: string; enabled: boolean; reload: () => Promise<unknown> }>()

async function set(enabled: boolean) {
	try {
		await setValue(props.doctype, props.name, { enabled: enabled ? 1 : 0 })
	} catch (error) {
		toast.error(errorText(error))
	}
	await props.reload()
}
</script>
