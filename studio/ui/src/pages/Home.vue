<template>
	<div class="isolate h-screen flex-col overflow-hidden bg-surface-base">
		<div
			class="toolbar sticky top-0 z-10 flex h-14 items-center justify-between border-b border-outline-gray-2 bg-surface-base px-3 py-2"
		>
			<router-link class="flex items-center gap-2" :to="{ name: 'StudioHome' }">
				<StudioLogo class="h-7 w-7"></StudioLogo>
				<h1 class="text-md-semibold mt-[2px] leading-5 text-ink-gray-7">Studio</h1>
			</router-link>
			<Button variant="solid" icon-left="lucide-plus" @click="showAppDialog = true">New App</Button>
		</div>

		<div class="flex h-full flex-col items-center px-20 py-10">
			<div class="flex w-full flex-row justify-between">
				<div class="text-lg-semibold text-ink-gray-7">Apps</div>
				<div class="relative flex items-center gap-2">
					<TabButtons
						v-model="appType"
						:options="[
							{ label: 'All', value: 'all' },
							{ label: 'Standard', value: 'standard' },
							{ label: 'Custom', value: 'custom' },
						]"
					/>
					<Input
						class="w-48"
						type="text"
						variant="outline"
						placeholder="Search"
						v-model="searchFilter"
						autofocus
						@input="
							(value: string) => {
								searchFilter = value
							}
						"
					>
						<template #prefix>
							<span class="lucide-search h-4 w-4 text-ink-gray-4" />
						</template>
					</Input>
				</div>
			</div>

			<section class="mt-5 w-full">
				<div v-if="!studioApps.data?.length && !searchFilter && appType === 'all'" class="col-span-full">
					<p class="mt-4 text-base text-ink-gray-4">
						You don't have any apps yet. Click on the "+ New App" button to create a new app
					</p>
				</div>
				<div v-else-if="!studioApps.data?.length" class="col-span-full">
					<p class="mt-4 text-base text-ink-gray-4">No matching apps found</p>
				</div>
				<div v-else class="grid w-full grid-cols-[repeat(auto-fill,minmax(14rem,1fr))] gap-5">
					<router-link
						class="group flex min-w-0 flex-col gap-1 rounded-6 border-2 p-4"
						v-for="app in studioApps.data"
						:to="{ name: 'StudioApp', params: { appID: app.name } }"
						:key="app.name"
					>
						<div class="flex h-7 flex-row items-center justify-between gap-2">
							<div class="truncate font-semibold text-ink-gray-7" :title="app.app_title">
								{{ app.app_title }}
							</div>
							<div class="invisible shrink-0 group-hover:visible has-[[data-state=open]]:visible">
								<Dropdown
									:options="[
										{
											label: 'Edit',
											onClick: () => {
												activeApp = app
												showAppDialog = true
											},
											icon: 'lucide-edit',
										},
										{
											label: 'View in Desk',
											onClick: () => openAppInDesk(app),
											icon: 'lucide-arrow-up-right',
										},
										{
											label: 'Delete',
											onClick: () => store.deleteApp(app.name, app.app_title),
											icon: 'lucide-trash-2',
											theme: 'red',
										},
									]"
									:button="{
										icon: 'lucide-more-horizontal',
										label: 'App Options',
										variant: 'ghost',
									}"
									size="sm"
									side="right"
								/>
							</div>
						</div>
						<UseTimeAgo v-slot="{ timeAgo }" :time="app.creation">
							<p class="mt-1 block text-xs text-ink-gray-4">Created {{ timeAgo }}</p>
						</UseTimeAgo>
					</router-link>
				</div>
			</section>
		</div>

		<AppDialog v-model:showDialog="showAppDialog" :app="activeApp" @after-leave="() => (activeApp = null)" />
	</div>
</template>

<script setup lang="ts">
import { onActivated, ref } from "vue"
import { Dropdown, Button, TabButtons } from "frappe-ui"
import { studioApps } from "@ui/data/studioApps"
import { UseTimeAgo } from "@vueuse/components"
import Input from "@ui/components/Input.vue"
import AppDialog from "@ui/components/AppDialog.vue"
import StudioLogo from "@ui/components/Icons/StudioLogo.vue"
import { watchDebounced } from "@vueuse/core"
import useStudioStore from "@ui/stores/studioStore"
import { openAppInDesk } from "@ui/utils/helpers"

const store = useStudioStore()

const searchFilter = ref("")
const appType = ref<"all" | "custom" | "standard">("all")

const fetchApps = () => {
	const filters = {} as any
	if (searchFilter.value) {
		filters["app_title"] = ["like", `%${searchFilter.value}%`]
	}
	if (appType.value !== "all") {
		filters["is_standard"] = appType.value === "standard" ? 1 : 0
	}
	studioApps.update({
		filters,
	})
	studioApps.fetch()
}

watchDebounced([searchFilter, appType], fetchApps, { debounce: 300, immediate: true })

const showAppDialog = ref(false)
const activeApp = ref()

// kept alive, so the title is set again on every return from an app
onActivated(() => (document.title = "Frappe Studio"))
</script>
