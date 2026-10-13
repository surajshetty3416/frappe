<template>
	<TabsRoot
		:model-value="section"
		orientation="vertical"
		activation-mode="manual"
		class="flex h-full min-h-0"
		@update:model-value="open"
	>
		<SettingsSidebar>
			<SettingsNavGroup>
				<SettingsNavItem v-for="item in sections" :key="item.value" :value="item.value">
					<template #prefix><span class="size-4 shrink-0 text-ink-gray-6" :class="item.icon" /></template>
					{{ item.label }}
				</SettingsNavItem>
			</SettingsNavGroup>
		</SettingsSidebar>
		<SettingsContent>
			<SettingsPanel v-for="item in sections" :key="item.value" :value="item.value">
				<div class="mx-auto flex min-h-0 w-full max-w-[760px] flex-1 flex-col">
					<component :is="item.component" />
				</div>
			</SettingsPanel>
		</SettingsContent>
	</TabsRoot>
</template>

<script setup lang="ts">
import { SettingsContent, SettingsNavGroup, SettingsNavItem, SettingsPanel, SettingsSidebar } from "frappe-ui"
import { TabsRoot } from "reka-ui"
import { computed } from "vue"
import { useRoute, useRouter } from "vue-router"

import Appearance from "./sections/Appearance.vue"
import Email from "./sections/Email.vue"
import Model from "./sections/Model.vue"
import People from "./sections/People.vue"

const sections = [
	{ value: "people", label: "People", icon: "lucide-users", component: People },
	{ value: "email", label: "Email", icon: "lucide-mail", component: Email },
	{ value: "model", label: "AI model", icon: "lucide-sparkles", component: Model },
	{ value: "appearance", label: "Appearance", icon: "lucide-sun-moon", component: Appearance },
]

const route = useRoute()
const router = useRouter()
const section = computed(() => String(route.params.section))
const open = (value: string | number) => router.replace({ name: "settings", params: { section: value } })
</script>
