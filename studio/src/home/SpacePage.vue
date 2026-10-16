<template>
	<div data-layer="shell" class="h-full overflow-y-auto">
		<div class="mx-auto flex w-full max-w-[1600px] flex-col gap-3 px-5 pb-28 pt-4">
			<div v-if="error" class="py-16 text-center text-sm text-ink-gray-5">{{ error }}</div>
			<template v-else-if="space">
				<header class="flex flex-wrap items-center gap-3">
					<span class="grid size-8 shrink-0 place-items-center rounded-4 bg-surface-gray-2 text-ink-gray-7">
						<span :class="spaceIcon(space.icon)" class="size-4" />
					</span>
					<div class="mr-auto min-w-0">
						<h1 class="truncate text-lg font-semibold text-ink-gray-9">{{ space.title }}</h1>
						<p v-if="space.description" class="truncate text-sm text-ink-gray-5">{{ space.description }}</p>
					</div>
					<template v-if="!editing">
						<!-- who is in it -->
						<div v-if="space.members.length" class="flex items-center gap-0.5" :title="space.members.map((member) => member.full_name).join(', ')">
							<Avatar v-for="member in space.members.slice(0, 4)" :key="member.user" :label="member.full_name" :image="member.image" size="sm" />
							<span v-if="space.members.length > 4" class="pl-1 text-xs tabular-nums text-ink-gray-5">+{{ space.members.length - 4 }}</span>
						</div>
						<Button size="sm" variant="ghost" icon-left="lucide-messages-square" label="Conversation" @click="pane = { open: true, tab: 'conversation' }" />
						<Button v-if="space.can_edit" size="sm" variant="ghost" icon-left="lucide-layout-dashboard" label="Arrange" @click="startEditing" />
						<Button v-if="!space.joined" size="sm" variant="solid" label="Join" :loading="joining" @click="join(true)" />
						<Dropdown v-else :options="[{ label: 'Leave Space', icon: 'lucide-log-out', onClick: () => join(false) }]" align="end">
							<Button size="sm" variant="ghost" icon="lucide-ellipsis" tooltip="More" :loading="joining" />
						</Dropdown>
					</template>
					<template v-else>
						<Button size="sm" label="Cancel" @click="editing = false" />
						<Button size="sm" variant="solid" label="Save" :loading="saving" @click="save" />
					</template>
				</header>
				<p v-if="editing" class="text-sm text-ink-gray-5">
					Move, resize or remove this Space's widgets. Mark what members should see on their Home by asking the assistant.
				</p>
				<WorkspaceGrid :widgets="editing ? draft : space.widgets" :editing="editing" @update="(widgets) => (draft = widgets)" />
				<p v-if="!space.widgets.length" class="py-10 text-center text-sm text-ink-gray-5">
					Nothing here yet. Ask the assistant to set this Space up from what the team does.
				</p>
			</template>
			<div v-else class="flex h-24 items-center justify-center">
				<LoadingIndicator class="size-4 text-ink-gray-5" />
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { Avatar, Button, Dropdown, LoadingIndicator, call } from "frappe-ui"
import { computed, onBeforeUnmount, ref, watch } from "vue"
import { useRoute } from "vue-router"

import WorkspaceGrid from "./WorkspaceGrid.vue"
import { type Space, type Widget, joinSpace, openSpace, openView, pane, refreshed, spaceIcon } from "./home"
import { errorText } from "./widgets/format"

const route = useRoute()
const name = computed(() => String(route.params.space))

const space = openSpace
const error = ref("")
const editing = ref(false)
const draft = ref<Widget[]>([])
const saving = ref(false)
async function load() {
	error.value = ""
	try {
		space.value = await call<Space>("frappe.ai.spaces.get_space", { space: name.value })
		document.title = space.value.title
	} catch (failure) {
		space.value = null
		error.value = errorText(failure)
	}
}
watch(name, () => {
	space.value = null
	openView.value = null
	editing.value = false
	load()
}, { immediate: true })
watch(refreshed, load)
onBeforeUnmount(() => (openSpace.value = null))

const joining = ref(false)
async function join(joined: boolean) {
	joining.value = true
	try {
		await joinSpace(name.value, joined)
		await load()
	} finally {
		joining.value = false
	}
}

function startEditing() {
	draft.value = JSON.parse(JSON.stringify(space.value?.widgets ?? []))
	editing.value = true
}
async function save() {
	saving.value = true
	try {
		await call("frappe.ai.spaces.save_space_widgets", { space: name.value, widgets: draft.value })
		editing.value = false
		await load()
	} finally {
		saving.value = false
	}
}
</script>
