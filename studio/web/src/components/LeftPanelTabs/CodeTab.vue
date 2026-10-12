<template>
	<div class="h-full">
		<PageScript
			:key="pageStore.selectedPage"
			v-if="pageStore.selectedPage && pageStore.activePage"
			:page="pageStore.activePage" />
	</div>
</template>
<script setup lang="ts">
import PageScript from "@builder/components/PageScript.vue";
import usePageStore from "@builder/stores/pageStore";

const pageStore = usePageStore();
</script>
