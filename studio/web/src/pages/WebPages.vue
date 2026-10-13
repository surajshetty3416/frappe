<template>
	<div class="h-full overflow-y-auto bg-surface-base">
		<div class="mx-auto flex max-w-3xl flex-col gap-4 px-6 py-8">
			<div class="flex items-center justify-between">
				<h1 class="text-xl font-semibold text-ink-gray-8">Websites</h1>
				<Button variant="solid" icon-left="lucide-plus" label="New page" :route="{ name: 'builder-editor', params: { pageId: 'new' } }" />
			</div>
			<div v-if="webPages.loading && !webPages.data?.length" class="flex flex-col gap-3 py-2">
				<Skeleton v-for="i in 3" :key="i" class="h-9 w-full" />
			</div>
			<p v-else-if="!webPages.data?.length" class="py-12 text-center text-base text-ink-gray-5">
				No pages yet. Ask the chat for one, or start a new page.
			</p>
			<List v-else class="-mx-3">
				<ListRows :items="webPages.data" v-slot="{ item }">
					<ListRow :route="{ name: 'builder-editor', params: { pageId: item.name } }">
						<ListCell><span class="lucide-globe size-4 text-ink-gray-5" /></ListCell>
						<ListCell>
							<div class="flex min-w-0 flex-col gap-0.5 text-left">
								<span class="truncate text-base text-ink-gray-8">{{ item.page_title || item.page_name }}</span>
								<span class="truncate text-sm text-ink-gray-5">/{{ (item.route || "").replace(/^\//, "") }}</span>
							</div>
						</ListCell>
						<ListCell class="gap-3 text-sm text-ink-gray-5">
							<span class="flex w-20 items-center gap-1.5">
								<span class="size-1.5 rounded-full" :class="item.published ? 'bg-surface-green-7' : 'bg-surface-gray-5'" />
								{{ item.published ? "Published" : "Draft" }}
							</span>
							<UseTimeAgo v-slot="{ timeAgo }" :time="item.modified">
								<span class="w-36 whitespace-nowrap text-right">Edited {{ timeAgo }}</span>
							</UseTimeAgo>
						</ListCell>
					</ListRow>
				</ListRows>
			</List>
		</div>
	</div>
</template>
<script setup lang="ts">
import { webPages } from "@web/data/webPage";
import { UseTimeAgo } from "@vueuse/components";
import { Button, Skeleton } from "frappe-ui";
import { List, ListCell, ListRow, ListRows } from "frappe-ui/list";
import { onActivated } from "vue";

// kept alive, so a page made or renamed elsewhere shows on return
onActivated(() => webPages.reload());
</script>
