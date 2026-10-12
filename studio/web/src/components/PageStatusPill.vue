<template>
	<Badge size="md">
		<template #prefix>
			<PageStatusDot :page="page" />
		</template>
		{{ label }}
	</Badge>
</template>
<script setup lang="ts">
import PageStatusDot from "@builder/components/PageStatusDot.vue";
import { BuilderPage } from "@builder/types/doctypes";
import { getPageStatus } from "@builder/utils/pageStatus";
import { Badge } from "frappe-ui";
import { computed } from "vue";

const props = defineProps<{
	page: BuilderPage;
}>();

const label = computed(() => getPageStatus(props.page).label);
</script>
