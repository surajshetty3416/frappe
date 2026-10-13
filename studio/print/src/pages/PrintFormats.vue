<template>
	<div class="h-full overflow-y-auto bg-surface-base">
		<div class="mx-auto flex max-w-3xl flex-col gap-4 px-6 py-8">
			<h1 class="text-xl font-semibold text-ink-gray-8">Print</h1>
			<div v-if="formats.loading && !formats.data?.length" class="flex flex-col gap-3 py-2">
				<Skeleton v-for="i in 3" :key="i" class="h-9 w-full" />
			</div>
			<p v-else-if="!formats.data?.length" class="py-12 text-center text-base text-ink-gray-5">
				No print formats yet. Ask the chat for a badge, an invoice or a certificate.
			</p>
			<List v-else class="-mx-3" :columns="['24px', 'minmax(0, 1fr)', '176px', '160px']" :row-height="56">
				<ListRows :items="formats.data" v-slot="{ item }">
					<ListRow :route="{ name: 'print-format', params: { format: item.name } }">
						<ListCell><span class="lucide-printer size-4 text-ink-gray-5" /></ListCell>
						<ListCell>
							<div class="flex min-w-0 flex-col gap-0.5 text-left">
								<span class="truncate text-base text-ink-gray-8">{{ item.name }}</span>
								<span class="truncate text-sm text-ink-gray-5">{{ [item.doc_type, item.canvas_blocks && item.page_size].filter(Boolean).join(" · ") }}</span>
							</div>
						</ListCell>
						<ListCell class="justify-end gap-1.5 text-sm text-ink-gray-5">
							<span class="size-1.5 shrink-0 rounded-full" :class="item.disabled ? 'bg-surface-gray-5' : 'bg-surface-green-7'" />
							{{ item.disabled ? "Disabled" : "Enabled" }}
						</ListCell>
						<ListCell class="justify-end text-sm text-ink-gray-5">
							<UseTimeAgo v-slot="{ timeAgo }" :time="item.modified">
								<span class="whitespace-nowrap">Edited {{ timeAgo }}</span>
							</UseTimeAgo>
						</ListCell>
					</ListRow>
				</ListRows>
			</List>
		</div>
	</div>
</template>
<script setup lang="ts">
import { UseTimeAgo } from "@vueuse/components"
import { Skeleton, createListResource } from "frappe-ui"
import { List, ListCell, ListRow, ListRows } from "frappe-ui/list"
import { onActivated } from "vue"

const formats = createListResource({
	doctype: "Print Format",
	fields: ["name", "doc_type", "disabled", "page_size", "canvas_blocks", "modified"],
	filters: { print_format_for: "DocType" },
	orderBy: "modified desc",
	pageLength: 100,
	auto: true,
})
onActivated(() => formats.reload())
</script>
