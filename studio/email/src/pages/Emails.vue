<template>
	<div class="h-full overflow-y-auto bg-surface-base">
		<div class="mx-auto flex max-w-3xl flex-col gap-4 px-6 py-8">
			<h1 class="text-xl font-semibold text-ink-gray-8">Email</h1>

			<div v-if="templates.loading && !templates.data?.length" class="flex flex-col gap-3 py-2">
				<Skeleton v-for="i in 3" :key="i" class="h-9 w-full" />
			</div>
			<List v-else class="-mx-3 list-row-px-3" :columns="COLUMNS" :row-height="56">
				<ListGroup label="Templates">
					<ListRows :items="templates.data ?? []" v-slot="{ item }">
						<ListRow :route="{ name: 'email-template', params: { template: item.name } }">
							<ListCell><span class="lucide-mail size-4 text-ink-gray-5" /></ListCell>
							<ListCell>
								<div class="flex min-w-0 flex-col gap-0.5 text-left">
									<span class="truncate text-base text-ink-gray-8">{{ item.name }}</span>
									<span class="truncate text-sm text-ink-gray-5">{{ sentWhen(senders[item.name]) }}</span>
								</div>
							</ListCell>
							<ListCell class="justify-end text-sm text-ink-gray-5"><span class="truncate">{{ item.reference_doctype }}</span></ListCell>
							<ListCell class="justify-end text-sm text-ink-gray-5">
								<UseTimeAgo v-slot="{ timeAgo }" :time="item.modified">
									<span class="whitespace-nowrap">Edited {{ timeAgo }}</span>
								</UseTimeAgo>
							</ListCell>
						</ListRow>
					</ListRows>
					<p v-if="!templates.data?.length" class="py-8 text-center text-base text-ink-gray-5">
						No email templates yet. Ask the chat for a confirmation email or an announcement.
					</p>
				</ListGroup>
				<ListGroup label="Groups" class="mt-6">
					<ListRows :items="groups.data ?? []" v-slot="{ item }">
						<ListRow>
							<ListCell><span class="lucide-users size-4 text-ink-gray-5" /></ListCell>
							<ListCell>
								<div class="flex min-w-0 flex-col gap-0.5 text-left">
									<span class="truncate text-base text-ink-gray-8">{{ item.title }}</span>
									<span class="truncate text-sm text-ink-gray-5">Email group</span>
								</div>
							</ListCell>
							<ListCell class="justify-end text-sm text-ink-gray-5">
								{{ item.total_subscribers.toLocaleString() }} {{ item.total_subscribers === 1 ? "member" : "members" }}
							</ListCell>
							<ListCell class="justify-end text-sm text-ink-gray-5">
								<UseTimeAgo v-slot="{ timeAgo }" :time="item.modified">
									<span class="whitespace-nowrap">Edited {{ timeAgo }}</span>
								</UseTimeAgo>
							</ListCell>
						</ListRow>
					</ListRows>
					<p v-if="!groups.loading && !groups.data?.length" class="py-8 text-center text-base text-ink-gray-5">
						No email groups yet. Ask the chat to put your attendees in one.
					</p>
				</ListGroup>
			</List>
		</div>
	</div>
</template>
<script setup lang="ts">
import { UseTimeAgo } from "@vueuse/components"
import { Skeleton, call, createListResource } from "frappe-ui"
import { List, ListCell, ListGroup, ListRow, ListRows } from "frappe-ui/list"
import { onActivated, ref } from "vue"

import { sentWhen } from "../senders"

const COLUMNS = ["24px", "minmax(0, 1fr)", "176px", "160px"]

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
