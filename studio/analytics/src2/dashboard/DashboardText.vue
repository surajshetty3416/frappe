<script setup lang="ts">
import DOMPurify from 'dompurify'
import { computed, defineAsyncComponent, inject, ref, shallowRef, watch } from 'vue'
import { WorkbookDashboardText } from '../types/workbook.types'
import { Dashboard } from './dashboard'
import { __ } from '../translation'

// Every page renders a text item through here, but only the editor provides a
// store and edits the text in place.
const dashboard = inject<Dashboard | undefined>('dashboard', undefined)
const props = defineProps<{ item: WorkbookDashboardText; editing?: boolean }>()
const emit = defineEmits<{ done: [] }>()

const editedText = ref(props.item.text)

// `frappe-ui/editor` is larger than the rest of the dashboard island, and a
// reader never edits, so the editor loads on the first edit, not with the page.
const editorModule = () => import('frappe-ui/editor')
const Editor = defineAsyncComponent(() => editorModule().then((module) => module.Editor))
const EditorContent = defineAsyncComponent(() =>
	editorModule().then((module) => module.EditorContent),
)
// `RichTextKit` is a value, not a component, so `defineAsyncComponent` cannot load it
const extensions = shallowRef<unknown[]>()
watch(
	() => props.editing,
	(open) => {
		if (!open) return
		editedText.value = props.item.text
		if (!extensions.value) editorModule().then((module) => (extensions.value = [module.RichTextKit]))
	},
	{ immediate: true },
)

function finish() {
	if (editedText.value !== props.item.text) props.item.text = editedText.value
	emit('done')
}

// A public link shows the text to a reader with no session. The dashboard
// sanitizes a text item on the way in; this is the second half of that rule.
const textHtml = computed(() => (props.item.text ? DOMPurify.sanitize(props.item.text) : ''))
</script>

<template>
	<!-- The editor's content is `contenteditable`, which the grid treats as a
	     control, so a press inside it edits instead of dragging the tile -->
	<div v-if="props.editing && extensions" class="h-full w-full overflow-auto">
		<Editor
			v-model="editedText"
			:extensions="extensions"
			:placeholder="__('Write in Markdown')"
			autofocus
			@blur="finish"
		>
			<template #default="{ editor }">
				<EditorContent
					:editor="editor"
					class="prose prose-v3 h-full max-w-none cursor-text text-ink-gray-7"
					@keydown.esc="finish"
				/>
			</template>
		</Editor>
	</div>
	<!-- centered with `my-auto` on the content rather than `justify-center` on the
	     box: a centered flex column scrolls away from text taller than the cell -->
	<div v-else-if="props.item.text" class="flex h-full w-full flex-col overflow-auto">
		<div class="prose prose-v3 my-auto max-w-none text-ink-gray-7" v-html="textHtml"></div>
	</div>
	<div v-else-if="dashboard" class="flex h-full w-full items-center text-p-sm text-ink-gray-4">
		{{ __('Double-click to add text') }}
	</div>
</template>
