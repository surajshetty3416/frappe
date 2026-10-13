<template>
	<Dialog
		v-model:open="showDialog"
		title="New App"
		width="md"
		@after-leave="
			() => {
				title = ''
				error = ''
			}
		"
	>
		<template #default>
			<FormControl label="Title" type="text" variant="outline" v-model="title" :required="true" autofocus />
			<ErrorMessage class="mt-2" :message="error" />
		</template>
		<template #actions>
			<div class="flex justify-end">
				<Button variant="solid" label="Create" :loading="studioApps.insert.loading" @click="createApp" />
			</div>
		</template>
	</Dialog>
</template>

<script lang="ts" setup>
import { ref } from "vue"
import { useRouter } from "vue-router"
import { Dialog, FormControl, ErrorMessage, Button } from "frappe-ui"
import { studioApps } from "@ui/data/studioApps"
import type { StudioApp } from "@ui/types/Studio/StudioApp"

const showDialog = defineModel("showDialog", { type: Boolean, required: true })
const title = ref("")
const error = ref("")
const router = useRouter()

// the app's name and route derive from its title
function createApp() {
	studioApps.insert.submit(
		{ app_title: title.value },
		{
			onSuccess(app: StudioApp) {
				showDialog.value = false
				router.push({ name: "StudioApp", params: { appID: app.name } })
			},
			onError(reqError: any) {
				error.value = reqError.messages.join(", ")
			},
		},
	)
}
</script>
