<template>
	<div>
		<CodeBlock :code="arguments.sql ?? ''" lang="sql" bare />
		<RecordTable v-if="query" :columns="columns" :rows="rows" />
	</div>
</template>

<script setup>
import { computed } from "vue";
import CodeBlock from "@flow/ui-core/components/CodeBlock.vue";

import RecordTable from "./RecordTable.vue";
import { parseResult } from "./result.js";

const props = defineProps({
	arguments: { type: Object, required: true },
	result: { type: Object, default: null },
});

const query = computed(() => parseResult(props.result));
const columns = computed(() => (query.value?.columns ?? []).map((column) => column.name));
// a row is a list of cells in column order, or a record
const rows = computed(() =>
	(query.value?.rows ?? []).map((row) => ({
		cells: Array.isArray(row) ? Object.fromEntries(columns.value.map((column, i) => [column, row[i]])) : row,
	}))
);
</script>
