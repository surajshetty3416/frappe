<template>
	<div class="relative h-full">
		<router-view v-slot="{ Component }">
			<keep-alive>
				<component :is="Component" />
			</keep-alive>
		</router-view>
	</div>
</template>
<script setup lang="ts">
import usePageStore from "@web/stores/pageStore";
import { useTitle } from "@vueuse/core";
import { computed } from "vue";
import { useRoute } from "vue-router";

const pageStore = usePageStore();
const route = useRoute();

useTitle(
	computed(() =>
		route.name === "builder-editor" && pageStore.activePage
			? pageStore.activePage.page_title || "Untitled page"
			: "Websites",
	),
);
</script>
