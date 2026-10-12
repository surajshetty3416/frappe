<template>
	<div>
		<Dropdown :options="menuOptions">
			<template v-slot="{ open }">
				<button
					class="flex h-12 items-center rounded-5 py-2 duration-300 ease-in-out"
					:class="
						props.isCollapsed
							? 'w-auto px-0'
							: open
							  ? 'w-52 bg-surface-elevation-2 px-2 shadow-sm'
							  : 'w-52 px-2 hover:bg-surface-gray-3'
					"
				>
					<img
						src="../assets/insights-logo-new.svg"
						alt="logo"
						class="h-8 w-8 flex-shrink-0 rounded-4"
					/>
					<div
						class="flex flex-1 flex-col text-left duration-300 ease-in-out"
						:class="
							props.isCollapsed
								? 'ml-0 w-0 overflow-hidden opacity-0'
								: 'ml-2 w-auto opacity-100'
						"
					>
						<div class="text-base-medium leading-none text-ink-gray-8">Insights</div>
					</div>
					<div
						class="duration-300 ease-in-out"
						:class="
							props.isCollapsed
								? 'ml-0 w-0 overflow-hidden opacity-0'
								: 'ml-2 w-auto opacity-100'
						"
					>
						<ChevronDown class="h-4 w-4 text-ink-gray-5" aria-hidden="true" />
					</div>
				</button>
			</template>
		</Dropdown>

		<Dialog
			v-model:open="showLoginToFCDialog"
			:title="__('Login to Frappe Cloud?')"
			:message="__('Are you sure you want to login to your Frappe Cloud dashboard?')"
			:actions="[
				{
					label: __('Confirm'),
					variant: 'solid',
					loading: loggingInToFC,
					onClick() {
						loginToFC()

						showLoginToFCDialog.value = false
					},
				},
			]"
		/>
	</div>
</template>

<script setup lang="ts">
import { call, Dropdown } from 'frappe-ui'
import { ChevronDown, HelpCircle, MessageCircle } from 'lucide-vue-next'
import { computed, h, ref } from 'vue'
import { showErrorToast } from '../helpers'
import FrappeCloudIcon from './Icons/FrappeCloudIcon.vue'
import { __ } from '../translation'

const props = defineProps<{ isCollapsed?: boolean }>()

const showLoginToFCDialog = ref(false)

const menuOptions = computed(() => {
	const options: { label: string; icon: any; onClick: () => void }[] = [
		{
			label: __('Documentation'),
			icon: h(HelpCircle),
			onClick: () => window.open('https://docs.frappe.io/insights', '_blank'),
		},
		{
			label: __('Join Telegram Group'),
			icon: h(MessageCircle),
			onClick: () => window.open('https://t.me/frappeinsights', '_blank'),
		},
	]

	if (window.is_fc_site) {
		options.push({
			icon: h(FrappeCloudIcon),
			label: __('Login to Frappe Cloud'),
			onClick: () => (showLoginToFCDialog.value = true),
		})
	}

	return options
})

const loggingInToFC = ref(false)
function loginToFC() {
	loggingInToFC.value = true
	call('frappe.integrations.frappe_providers.frappecloud_billing.current_site_info')
		.then((data: any) => {
			if (!data.base_url || !data.site_name) {
				throw new Error('Invalid response')
			}
			window.open(`${data.base_url}/dashboard/sites/${data.site_name}`, '_blank')
		})
		.catch(showErrorToast)
		.finally(() => {
			loggingInToFC.value = false
		})
}
</script>
