<template>
	<Dropdown :options="options" align="start">
		<template #default="{ open }">
			<Button variant="ghost">
				<span class="text-base text-ink-gray-8">{{ store.activeApp?.app_title }}</span>
				<span v-if="store.activePage" class="ml-1.5 text-base text-ink-gray-5">{{ store.activePage.page_title }}</span>
				<template #suffix>
					<span :class="open ? 'lucide-chevron-up' : 'lucide-chevron-down'" class="h-4 w-4 text-ink-gray-5" />
				</template>
			</Button>
		</template>
		<template #item-suffix="{ item }">
			<Badge v-if="item.label === homeTitle" size="sm">Home</Badge>
		</template>
	</Dropdown>
</template>

<script setup lang="ts">
import { computed } from "vue"
import { useRouter } from "vue-router"
import { Badge, Button, Dropdown } from "frappe-ui"
import useStudioStore from "@ui/stores/studioStore"

const store = useStudioStore()
const router = useRouter()

const openPage = (pageID: string) =>
	router.push({ name: "StudioPage", params: { appID: store.activeApp!.name, pageID } })

const homeTitle = computed(() => {
	const home = store.activeApp?.app_home
	return home ? store.appPages[home]?.page_title : null
})

const options = computed(() => [
	{
		group: "Pages",
		hideLabel: true,
		options: Object.values(store.appPages).map((page) => ({
			label: page.page_title || page.name,
			icon: store.activePage?.name === page.name ? "lucide-check" : "lucide-file",
			onClick: () => openPage(page.name),
		})),
	},
	{
		group: "New",
		hideLabel: true,
		options: [{ label: "New Page", icon: "lucide-plus", onClick: () => openPage("new") }],
	},
])
</script>
