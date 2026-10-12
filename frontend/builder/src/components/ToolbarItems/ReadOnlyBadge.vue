<template>
	<div class="flex items-center gap-2">
		<Badge variant="subtle" theme="amber">
			{{ pageStore.activePage?.is_template ? __("Template") : __("Read Only") }}
		</Badge>
		<Button
			v-if="pageStore.activePage?.is_template && pageStore.activePage?.template_group"
			size="sm"
			variant="subtle"
			@click="duplicateToEdit">
			{{ __("Duplicate to edit") }}
		</Button>
	</div>
</template>
<script setup lang="ts">
import { __ } from "@builder/translation";
import router from "@builder/router";
import usePageStore from "@builder/stores/pageStore";
import { Badge, createResource, toast } from "frappe-ui";

const pageStore = usePageStore();

const duplicateToEdit = async () => {
	toast.promise(
		createResource({
			url: "frappe.builder.api.create_page_from_template",
		})
			.submit({ template_page: pageStore.activePage?.name })
			.then((newPageName: string) => {
				router.push({ name: "builder-editor", params: { pageId: newPageName }, force: true });
				pageStore.setPage(newPageName);
			}),
		{
			loading: __("Creating an editable copy..."),
			success: () => __("Page created"),
			error: () => __("Could not create page from template"),
		},
	);
};
</script>
