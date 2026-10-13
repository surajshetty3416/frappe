<template>
	<div v-if="app" class="flex flex-col gap-5 p-3">
		<section class="flex flex-col gap-4">
			<span class="text-base font-medium text-ink-gray-8">App</span>
			<Input
				label="Title"
				:modelValue="app.app_title"
				:hideClearButton="true"
				@update:modelValue="(value: string) => updateApp('app_title', value)"
			/>
			<Input
				type="select"
				label="App Home"
				:options="homeOptions"
				:modelValue="app.app_home"
				@update:modelValue="(value: string) => updateApp('app_home', value)"
			/>
			<Input
				label="Route"
				:description="appURL"
				:modelValue="app.route"
				:hideClearButton="true"
				@update:modelValue="(value: string) => updateApp('route', value)"
			/>
			<div class="flex items-center gap-3">
				<img :src="app.favicon || defaultFavicon" alt="" class="size-6 rounded-4" />
				<FileUploader
					file-types="image/*"
					:private="false"
					doctype="Studio App"
					:docname="app.name"
					@success="(file: FileDoc) => updateApp('favicon', file.file_url)"
				>
					<template #default="{ uploading, progress, openFileSelector }">
						<div class="flex gap-2">
							<Button @click="openFileSelector">
								{{ uploading ? `Uploading ${progress}%` : app.favicon ? "Change Favicon" : "Upload Favicon" }}
							</Button>
							<Button v-if="app.favicon" @click="updateApp('favicon', '')">Remove</Button>
						</div>
					</template>
				</FileUploader>
			</div>
		</section>

		<section v-if="page" class="flex flex-col gap-4 border-t border-outline-gray-2 pt-5">
			<span class="text-base font-medium text-ink-gray-8">Page</span>
			<PageMetaFields
				:appRoute="app.route"
				:title="page.page_title || ''"
				:route="page.route"
				:allowGuest="Boolean(page.allow_guest)"
				@update:title="(value: string) => store.updateActivePage('page_title', value)"
				@update:route="(value: string) => store.updateActivePage('route', value)"
				@update:allowGuest="(value: boolean) => store.updateActivePage('allow_guest', value ? 1 : 0)"
			/>
			<!-- values the preview uses for the route's variables, e.g. :proposal in /proposals/:proposal -->
			<Input
				v-for="name in routeVariableNames"
				:key="name"
				:label="`Preview ${name.replace(/_/g, ' ')}`"
				:hideClearButton="true"
				:modelValue="store.routeVariables[name] || ''"
				@update:modelValue="(value: string) => store.setRouteVariable(name, value)"
			/>
		</section>

		<section class="border-t border-outline-gray-2 pt-5">
			<Button theme="red" variant="subtle" @click="store.unpublishApp()">Unpublish</Button>
		</section>
	</div>
</template>

<script setup lang="ts">
import { computed } from "vue"
import { Button, FileUploader, toast } from "frappe-ui"
import Input from "@ui/components/Input.vue"
import PageMetaFields from "@ui/components/PageMetaFields.vue"
import useStudioStore from "@ui/stores/studioStore"
import { getRouteVariables } from "@ui/utils/helpers"
import defaultFavicon from "/studio-favicon.png"

type FileDoc = { file_url: string }

// The app's and the open page's settings, for the Details drawer
const store = useStudioStore()
const app = computed(() => store.activeApp)
const page = computed(() => store.activePage)
const appURL = computed(() => `${window.location.origin}/${app.value?.route}`)
const homeOptions = computed(() =>
	Object.values(store.appPages).map((page) => ({ label: page.page_title, value: page.name })),
)
const routeVariableNames = computed(() => getRouteVariables(page.value?.route || ""))

const FIELD_LABELS = { app_title: "Title", route: "Route", app_home: "App Home", favicon: "Favicon" }

function updateApp(field: keyof typeof FIELD_LABELS, value: string) {
	const label = FIELD_LABELS[field]
	store
		.updateActiveApp(field, value)
		.then(() => toast.success(`${label} saved`))
		.catch((error: any) => {
			toast.error(`Could not save ${label}`, { description: error?.messages?.join(", ") || error?.message })
		})
}
</script>
