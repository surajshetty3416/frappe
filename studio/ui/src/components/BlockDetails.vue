<template>
	<div class="flex flex-col">
		<div v-if="block" class="flex flex-col gap-3 p-3">
			<span class="text-base font-medium text-ink-gray-8">{{ block.getBlockDescription() }}</span>
			<TabButtons v-model="tab" :options="tabs.map((label) => ({ label, value: label }))" />
		</div>
		<ComponentProperties
			v-show="tab === 'Properties' || (tab === 'Styles' && blockController.isText())"
			class="p-3"
			:block="block"
		/>
		<ComponentStyles v-show="tab === 'Styles'" class="p-3" :block="block" />
		<ComponentEvents v-show="tab === 'Events'" class="p-3" :block="block" />

		<Dialog
			v-model="canvasStore.showHTMLDialog"
			:title="`Edit HTML - ${canvasStore.editableBlock?.componentName}`"
			size="7xl"
		>
			<template #default>
				<Code
					:modelValue="canvasStore.editableBlock?.getHTML()"
					language="html"
					:showLineNumbers="true"
					:showSaveButton="true"
					:completions="(context: CompletionContext) => getCompletions(context, canvasStore.editableBlock?.getCompletions())"
					@save="
						(value: string) => {
							canvasStore.editableBlock?.setHTML(value)
							canvasStore.closeHTMLDialog()
						}
					"
					height="500px"
					max-height="500px"
				/>
			</template>
		</Dialog>

		<Dialog
			v-model="canvasStore.showCodeDialog"
			:title="`Edit ${canvasStore.editableBlock?.componentName} prop - ${canvasStore.editableCode.propName}`"
			size="7xl"
		>
			<template #default>
				<Code
					:modelValue="canvasStore.editableCode.code"
					language="javascript"
					:showLineNumbers="true"
					:showSaveButton="true"
					:completions="dynamicValueCompletions"
					:overrideCompletions="true"
					@save="
						(value: string) => {
							canvasStore.editableBlock?.setProp(canvasStore.editableCode.propName, value)
							canvasStore.showCodeDialog = false
						}
					"
					:emitOnChange="true"
					height="500px"
					max-height="500px"
				/>
			</template>
		</Dialog>
	</div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue"
import { Dialog, TabButtons } from "frappe-ui"
import type { CompletionContext } from "@codemirror/autocomplete"

import ComponentProperties from "@ui/components/ComponentProperties.vue"
import ComponentStyles from "@ui/components/ComponentStyles.vue"
import ComponentEvents from "@ui/components/ComponentEvents.vue"
import Code from "@ui/components/Code.vue"
import useCanvasStore from "@ui/stores/canvasStore"
import blockController from "@ui/utils/blockController"
import { useStudioCompletions, useDynamicValueCompletions } from "@ui/utils/completions/useStudioCompletions"

// The selected block's props, styles and events, for the Details drawer
const canvasStore = useCanvasStore()
const block = computed(() => canvasStore.activeCanvas?.selectedBlocks[0])

const getCompletions = useStudioCompletions()
// created once: a fresh array would make Code.vue rebuild its extensions on every render
const dynamicValueCompletions = useDynamicValueCompletions()(() => canvasStore.editableBlock?.getCompletions())

// containers and the page root have no props; text shows its props with its styles
const hasProperties = computed(
	() => !(blockController.isRoot() || blockController.isContainer() || blockController.isText()),
)
const tabs = computed(() => (hasProperties.value ? ["Properties", "Styles", "Events"] : ["Styles", "Events"]))
const tab = ref("Properties")
watch(
	tabs,
	() => {
		if (!tabs.value.includes(tab.value)) tab.value = tabs.value[0]
	},
	{ immediate: true },
)
</script>
