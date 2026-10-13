<template>
	<div class="flex flex-1 flex-col items-center justify-center px-6 text-center">
		<span class="lucide-rows-3 size-5 text-ink-gray-4" />
		<p class="mt-3 text-base font-medium text-ink-gray-8">No {{ doctype.name }} records yet</p>
		<Button class="mt-4" variant="solid" label="New record" icon-left="lucide-plus" @click="newRecord" />
		<Button v-if="editable" class="mt-1" variant="ghost" label="or fill with demo data" @click="doctype.demoData = true" />
	</div>
</template>

<script setup lang="ts">
import { Button } from "frappe-ui"
import { useRoute, useRouter } from "vue-router"

import { doctype, editable } from "../doctype"

const route = useRoute()
const router = useRouter()
const newRecord = () => router.replace({ query: { ...route.query, view: "form", record: "new" } })
</script>
