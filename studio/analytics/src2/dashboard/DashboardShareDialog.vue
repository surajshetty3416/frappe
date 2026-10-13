<script setup lang="ts">
import { Switch, toast } from 'frappe-ui'
import { computed, ref } from 'vue'
import UserSelector from '../components/UserSelector.vue'
import { copy, copyToClipboard } from '../helpers'
import useUserStore from '../users/users'
import useDashboard from './dashboard'
import { __ } from '../translation'

// Share: a public link, and the people who may open the dashboard. Who else in
// the organization may read it is a setting, not a share.
const props = defineProps<{ name: string }>()
const show = defineModel<boolean>()

const dashboard = useDashboard(props.name)

const isPublic = ref(dashboard.doc.visibility === 'Public')
const peopleWithAccess = ref(copy(dashboard.doc.people_with_access || []))

const shareLink = computed(() => dashboard.getShareLink())

const hasChanged = computed(
	() =>
		isPublic.value !== (dashboard.doc.visibility === 'Public') ||
		JSON.stringify(peopleWithAccess.value.map((u) => u.email)) !==
			JSON.stringify((dashboard.doc.people_with_access || []).map((u) => u.email)),
)

async function saveChanges() {
	const wasPublic = dashboard.doc.visibility === 'Public'
	if (isPublic.value !== wasPublic) {
		dashboard.doc.visibility = isPublic.value ? 'Public' : 'Private'
		await dashboard.save()
	}
	await dashboard.updateAccess({
		people_with_access: peopleWithAccess.value.map((u) => u.email),
	})
	toast.success(__('Sharing updated'))
	show.value = false
}

const selectedUserEmail = ref<string>('')
const userStore = useUserStore()
function addSharedUser() {
	if (!selectedUserEmail.value) return
	peopleWithAccess.value.push({
		email: selectedUserEmail.value,
		full_name: userStore.getName(selectedUserEmail.value),
		user_image: userStore.getImage(selectedUserEmail.value),
	})
	selectedUserEmail.value = ''
}
</script>

<template>
	<Dialog
		v-model:open="show"
		:title="__('Share')"
		:actions="[{ label: __('Done'), variant: 'solid', disabled: !hasChanged, onClick: saveChanges }]"
	>
		<template #default>
			<div class="flex flex-col gap-4">
				<div class="flex items-center justify-between gap-2">
					<div class="flex flex-col">
						<span class="text-base text-ink-gray-8">{{ __('Public link') }}</span>
						<span class="text-p-sm text-ink-gray-5">
							{{ __('Anyone with the link can view, without signing in.') }}
						</span>
					</div>
					<div class="flex items-center gap-2">
						<Button
							v-if="isPublic"
							icon="lucide-link-2"
							:tooltip="__('Copy link')"
							@click="copyToClipboard(shareLink)"
						/>
						<Switch v-model="isPublic" />
					</div>
				</div>

				<hr class="border-t border-outline-gray-1" />

				<div class="flex gap-2">
					<div class="flex-1">
						<UserSelector
							v-model="selectedUserEmail"
							:placeholder="__('Add people by name or email')"
							:hide-users="peopleWithAccess.map((u) => u.email)"
						/>
					</div>
					<Button
						variant="solid"
						:label="__('Add')"
						:disabled="!selectedUserEmail"
						@click="addSharedUser"
					/>
				</div>
				<div v-if="peopleWithAccess.length" class="flex flex-col gap-1 overflow-y-auto">
					<div
						v-for="user in peopleWithAccess"
						:key="user.email"
						class="flex w-full items-center gap-2 py-1"
					>
						<Avatar size="lg" :label="user.full_name" :image="user.user_image" />
						<div class="flex flex-1 flex-col">
							<div class="text-base text-ink-gray-8">{{ user.full_name }}</div>
							<div class="text-p-sm text-ink-gray-5">{{ user.email }}</div>
						</div>
						<Button
							variant="ghost"
							icon="lucide-x"
							@click="peopleWithAccess.splice(peopleWithAccess.indexOf(user), 1)"
						/>
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>
