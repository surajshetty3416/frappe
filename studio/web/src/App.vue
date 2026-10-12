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
import useBuilderStore from "@web/stores/builderStore";
import usePageStore from "@web/stores/pageStore";
import { __ } from "@web/translation";
import { useTitle } from "@vueuse/core";
import { useSiteReadOnlyNotice } from "@web/utils/useSiteReadOnlyNotice";
import { computed } from "vue";
import { useRoute } from "vue-router";

// do not remove this
const builderStore = useBuilderStore();
const pageStore = usePageStore();
const route = useRoute();

const title = computed(() => {
	return pageStore.activePage && route.name !== "builder-home"
		? `${pageStore.activePage.page_title || __("Untitled")} | Builder`
		: "Frappe Builder";
});

useTitle(title);

useSiteReadOnlyNotice();
</script>
