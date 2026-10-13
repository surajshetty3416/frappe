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
				<List v-else class="-mx-3" :columns="COLUMNS">
					<ListRows :items="templates.data" v-slot="{ item }">
						<ListRow :route="{ name: 'email-template', params: { template: item.name } }">
							<ListCell><span class="lucide-mail size-4 text-ink-gray-5" /></ListCell>
							<ListCell>
								<div class="flex min-w-0 flex-col gap-0.5 text-left">
									<span class="truncate text-base text-ink-gray-8">{{ item.name }}</span>
									<span class="truncate text-sm text-ink-gray-5">{{ senders[item.name]?.join(", ") || item.subject }}</span>
								</div>
							</ListCell>
							<ListCell class="text-sm text-ink-gray-5"><span class="truncate">{{ item.reference_doctype }}</span></ListCell>
							<ListCell class="justify-end text-sm text-ink-gray-5">
								<UseTimeAgo v-slot="{ timeAgo }" :time="item.modified">
									<span class="whitespace-nowrap">Edited {{ timeAgo }}</span>
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
				<List v-else class="-mx-3" :columns="COLUMNS">
					<ListRows :items="groups.data ?? []" v-slot="{ item }">
						<ListRow>
							<ListCell><span class="lucide-users size-4 text-ink-gray-5" /></ListCell>
							<ListCell>
								<div class="flex min-w-0 flex-col gap-0.5 text-left">
									<span class="truncate text-base text-ink-gray-8">{{ item.title }}</span>
									<span class="truncate text-sm text-ink-gray-5">Email group</span>
								</div>
							</ListCell>
							<ListCell class="text-sm text-ink-gray-5">
								{{ item.total_subscribers }} {{ item.total_subscribers === 1 ? "member" : "members" }}
							</ListCell>
							<ListCell class="justify-end text-sm text-ink-gray-5">
								<UseTimeAgo v-slot="{ timeAgo }" :time="item.modified">
									<span class="whitespace-nowrap">Edited {{ timeAgo }}</span>
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
import { Skeleton, call, createListResource } from "frappe-ui"
import { List, ListCell, ListRow, ListRows } from "frappe-ui/list"
import { onActivated, ref } from "vue"

// both sections share one grid, so their columns line up
const COLUMNS = ["24px", "minmax(0, 1fr)", "160px", "180px"]

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
const senders = ref<Record<string, string[]>>({})
const loadSenders = () => call("frappe.web.output.email_template.senders").then((sent) => (senders.value = sent as Record<string, string[]>))
loadSenders()
onActivated(() => {
	templates.reload()
	groups.reload()
	loadSenders()
})
</script>
