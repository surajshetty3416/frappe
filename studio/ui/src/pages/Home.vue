<template>
	<div class="flex h-screen flex-col overflow-hidden bg-surface-base">
		<div class="flex h-12 shrink-0 items-center justify-between border-b border-outline-gray-2 px-5">
			<h1 class="text-lg font-semibold text-ink-gray-8">Apps</h1>
			<div class="flex items-center gap-2">
				<Input
					class="w-48"
					type="text"
					variant="outline"
					placeholder="Search"
					v-model="searchFilter"
					@input="(value: string) => (searchFilter = value)"
				>
					<template #prefix>
						<span class="lucide-search h-4 w-4 text-ink-gray-4" />
					</template>
				</Input>
				<Button variant="solid" icon-left="lucide-plus" @click="showAppDialog = true">New App</Button>
			</div>
		</div>

		<section class="overflow-y-auto p-5">
			<p v-if="!studioApps.data?.length" class="text-base text-ink-gray-5">
				{{ searchFilter ? "No matching apps" : "No apps yet" }}
			</p>
			<div v-else class="grid w-full grid-cols-[repeat(auto-fill,minmax(14rem,1fr))] gap-4">
				<router-link
					v-for="app in studioApps.data"
					:key="app.name"
					class="group flex min-w-0 flex-col gap-1 rounded-6 border border-outline-gray-2 p-4 hover:border-outline-gray-3"
					:to="{ name: 'StudioApp', params: { appID: app.name } }"
				>
					<div class="flex h-7 items-center justify-between gap-2">
						<span class="truncate text-base font-medium text-ink-gray-8" :title="app.app_title">
							{{ app.app_title }}
						</span>
						<div class="invisible shrink-0 group-hover:visible has-[[data-state=open]]:visible">
							<Dropdown
								:options="[
									{
										label: 'Delete',
										icon: 'lucide-trash-2',
										theme: 'red',
										onClick: () => store.deleteApp(app.name, app.app_title),
									},
								]"
								:button="{ icon: 'lucide-more-horizontal', label: 'App Options', variant: 'ghost' }"
								size="sm"
								side="right"
							/>
						</div>
					</div>
					<UseTimeAgo v-slot="{ timeAgo }" :time="app.creation">
						<p class="text-sm text-ink-gray-5">Created {{ timeAgo }}</p>
					</UseTimeAgo>
				</router-link>
			</div>
		</section>

		<AppDialog v-model:showDialog="showAppDialog" />
	</div>
</template>

<script setup lang="ts">
import { onActivated, ref } from "vue"
import { Dropdown, Button } from "frappe-ui"
import { UseTimeAgo } from "@vueuse/components"
import { watchDebounced } from "@vueuse/core"
import { studioApps } from "@ui/data/studioApps"
import Input from "@ui/components/Input.vue"
import AppDialog from "@ui/components/AppDialog.vue"
import useStudioStore from "@ui/stores/studioStore"

const store = useStudioStore()

const searchFilter = ref("")
const showAppDialog = ref(false)

const fetchApps = () => {
	studioApps.update({ filters: searchFilter.value ? { app_title: ["like", `%${searchFilter.value}%`] } : {} })
	studioApps.fetch()
}

watchDebounced(searchFilter, fetchApps, { debounce: 300, immediate: true })

// kept alive, so the title is set again on every return from an app
onActivated(() => (document.title = "Apps"))
</script>
