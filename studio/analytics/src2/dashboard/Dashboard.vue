<script setup lang="ts">
import { Button } from 'frappe-ui'
import { ref, watchEffect } from 'vue'
import ContentEditable from '../components/ContentEditable.vue'
import { __ } from '../translation'
import useDashboard from './dashboard'
import DashboardPreview from './DashboardPreview.vue'
import DashboardShareDialog from './DashboardShareDialog.vue'

// The dashboard route: its title and Share above the preview, until the editor
// shell's artifact bar holds them.
const props = defineProps<{ name: string }>()

const store = useDashboard(props.name)
const showShare = ref(false)

function rename(title: string) {
	if (title && title !== store.doc.title) store.doc.title = title
}

watchEffect(() => (document.title = store.doc.title || __('Dashboard')))
</script>

<template>
	<div class="flex h-full w-full flex-col overflow-hidden">
		<div class="flex h-12 flex-shrink-0 items-center justify-between gap-2 border-b px-4">
			<ContentEditable
				class="cursor-text text-lg-semibold text-ink-gray-8"
				:modelValue="store.doc.title"
				:placeholder="__('Untitled dashboard')"
				@returned="rename"
				@blur="rename"
			/>
			<Button
				v-if="store.doc.can_share"
				variant="solid"
				:label="__('Share')"
				@click="showShare = true"
			/>
		</div>
		<DashboardPreview :key="props.name" class="min-h-0 flex-1" :name="props.name" />
		<DashboardShareDialog v-if="showShare" v-model="showShare" :name="props.name" />
	</div>
</template>
