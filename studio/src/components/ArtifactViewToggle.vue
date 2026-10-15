<template>
	<TabButtons
		v-model="artifactView"
		variant="ghost"
		:options="[
			{ value: 'grid', label: 'Grid', icon: 'lucide-layout-grid' },
			{ value: 'list', label: 'List', icon: 'lucide-list' },
		]"
	/>
</template>

<script setup lang="ts">
import { TabButtons } from "frappe-ui"

import { artifactView } from "../layout"
</script>
