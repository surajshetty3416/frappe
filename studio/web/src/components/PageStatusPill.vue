<template>
	<Badge size="md">
		<template #prefix>
			<PageStatusDot :page="page" />
		</template>
		{{ label }}
	</Badge>
</template>
<script setup lang="ts">
import PageStatusDot from "@web/components/PageStatusDot.vue";
import { BuilderPage } from "@web/types/doctypes";
import { getPageStatus } from "@web/utils/pageStatus";
import { Badge } from "frappe-ui";
import { computed } from "vue";

const props = defineProps<{
	page: BuilderPage;
}>();

const label = computed(() => getPageStatus(props.page).label);
</script>
