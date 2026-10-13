<template>
	<div class="h-full overflow-y-auto bg-surface-base">
		<div class="mx-auto flex max-w-3xl flex-col gap-8 px-6 py-8">
			<h1 class="text-xl font-semibold text-ink-gray-8">Email</h1>

			<section class="flex flex-col gap-2">
				<h2 class="text-sm font-medium text-ink-gray-5">Templates</h2>
				<div v-if="templates.loading && !templates.data?.length" class="flex flex-col gap-3 py-2">
					<Skeleton v-for="i in 3" :key="i" class="h-9 w-full" />
				</div>
				<p v-else-if="!templates.data?.length" class="py-8 text-center text-base text-ink-gray-5">
					No email templates yet. Ask the chat for a confirmation email or an announcement.
				</p>
				<List v-else class="-mx-3">
					<ListRows :items="templates.data" v-slot="{ item }">
						<ListRow :route="{ name: 'email-template', params: { template: item.name } }">
							<ListCell><span class="lucide-mail size-4 text-ink-gray-5" /></ListCell>
							<ListCell>
								<div class="flex min-w-0 flex-col gap-0.5 text-left">
									<span class="truncate text-base text-ink-gray-8">{{ item.name }}</span>
									<span class="truncate text-sm text-ink-gray-5">{{ item.subject }}</span>
								</div>
							</ListCell>
							<ListCell class="gap-3 text-sm text-ink-gray-5">
								<span class="w-32 truncate">{{ item.reference_doctype }}</span>
								<UseTimeAgo v-slot="{ timeAgo }" :time="item.modified">
									<span class="w-36 whitespace-nowrap text-right">Edited {{ timeAgo }}</span>
								</UseTimeAgo>
							</ListCell>
						</ListRow>
					</ListRows>
				</List>
			</section>

			<section class="flex flex-col gap-2">
				<h2 class="text-sm font-medium text-ink-gray-5">Groups</h2>
				<p v-if="!groups.loading && !groups.data?.length" class="py-8 text-center text-base text-ink-gray-5">
					No email groups yet. Ask the chat to put your attendees in one.
				</p>
				<List v-else class="-mx-3">
					<ListRows :items="groups.data ?? []" v-slot="{ item }">
						<ListRow>
							<ListCell><span class="lucide-users size-4 text-ink-gray-5" /></ListCell>
							<ListCell>
								<span class="truncate text-base text-ink-gray-8">{{ item.title }}</span>
							</ListCell>
							<ListCell class="gap-3 text-sm text-ink-gray-5">
								<span class="w-32">{{ item.total_subscribers }} {{ item.total_subscribers === 1 ? "member" : "members" }}</span>
								<UseTimeAgo v-slot="{ timeAgo }" :time="item.modified">
									<span class="w-36 whitespace-nowrap text-right">Edited {{ timeAgo }}</span>
								</UseTimeAgo>
							</ListCell>
						</ListRow>
					</ListRows>
				</List>
			</section>
		</div>
	</div>
</template>
<script setup lang="ts">
import { UseTimeAgo } from "@vueuse/components"
import { Skeleton, createListResource } from "frappe-ui"
import { List, ListCell, ListRow, ListRows } from "frappe-ui/list"
import { onActivated } from "vue"

const templates = createListResource({
	doctype: "Email Template",
	fields: ["name", "subject", "reference_doctype", "modified"],
	orderBy: "modified desc",
	pageLength: 100,
	auto: true,
})
const groups = createListResource({
	doctype: "Email Group",
	fields: ["name", "title", "total_subscribers", "modified"],
	orderBy: "modified desc",
	pageLength: 100,
	auto: true,
})
onActivated(() => {
	templates.reload()
	groups.reload()
})
</script>
