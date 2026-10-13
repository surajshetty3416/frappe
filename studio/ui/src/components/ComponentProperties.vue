<template>
	<div class="flex select-none flex-col pb-16" v-if="filteredSections.length">
		<EmptyState v-if="mixedTypeSelection" message="Select blocks of the same component to edit properties" />
		<EmptyState v-else-if="!block?.componentName" message="Select a block to edit properties" />
		<div v-else class="flex flex-col gap-3">
			<!-- props -->
			<SectionContainer title="Props" v-show="filteredSections.includes('props')">
				<PropsEditor ref="propsEditor" :block="block" :multiEdit="multipleBlocksSelected" />
			</SectionContainer>

			<!-- Visibility Condition -->
			<CollapsibleSection
				v-show="filteredSections.includes('visibility')"
				sectionName="Visibility Condition"
				:sectionCollapsed="toValue(sections.visibility?.collapsed)"
			>
				<template #actions>
					<Button
						v-if="block?.hasVisibilityCondition()"
						title="Toggle visibility condition"
						variant="ghost"
						@click.stop="block?.toggleVisibilityCondition()"
					>
						<span :class="block.visibilityCondition ? 'lucide-zap' : 'lucide-zap-off'" class="h-3 w-3" />
					</Button>
				</template>
				<Code
					language="javascript"
					height="60px"
					:showLineNumbers="false"
					:completions="(context: CompletionContext) => getCompletions(context, block?.getCompletions())"
					:modelValue="block?.visibilityCondition || block?.__lastVisibilityCondition"
					:readonly="!!block.__lastVisibilityCondition"
					@update:modelValue="blockController.setKeyValue('visibilityCondition', $event)"
				/>
			</CollapsibleSection>

			<!-- attributes -->
			<CollapsibleSection
				v-show="filteredSections.includes('attributes')"
				sectionName="Attributes"
				:sectionCollapsed="toValue(sections.attributes?.collapsed)"
			>
				<ObjectEditor
					ref="attributesEditor"
					:obj="blockController.getAttributes() || {}"
					@update:obj="(obj: Record<string, any>) => blockController.setAttributes(obj)"
					description="Pass additional HTML attributes or props that are not explicitly defined in the component"
				/>
			</CollapsibleSection>
		</div>
	</div>
</template>

<script setup lang="ts">
import { ref, computed, toValue } from "vue"
import { Button } from "frappe-ui"
import Block from "@ui/utils/block"
import PropsEditor from "@ui/components/PropsEditor.vue"
import ObjectEditor from "@ui/components/ObjectEditor.vue"
import EmptyState from "@ui/components/EmptyState.vue"
import SectionContainer from "@ui/components/SectionContainer.vue"
import CollapsibleSection from "@ui/components/CollapsibleSection.vue"
import { isObjectEmpty } from "@ui/utils/helpers"
import Code from "@ui/components/Code.vue"
import blockController from "@ui/utils/blockController"
import { useStudioCompletions } from "@ui/utils/completions/useStudioCompletions"
import type { CompletionContext } from "@codemirror/autocomplete"


const props = defineProps<{
	block?: Block
}>()
const getCompletions = useStudioCompletions()

const multipleBlocksSelected = computed(() => blockController.multipleBlocksSelected())
const mixedTypeSelection = computed(
	() => multipleBlocksSelected.value && !blockController.selectedBlocksHaveSameType(),
)

const attributesEditor = ref<InstanceType<typeof ObjectEditor> | null>(null)
const propsEditor = ref<InstanceType<typeof PropsEditor> | null>(null)

const sections: Record<string, { condition?: any; collapsed?: any; searchKeyWords: string }> = {
	props: {
		condition: computed(() => !props.block?.isContainer()),
		searchKeyWords: "Props, Properties, Inputs",
	},
	visibility: {
		collapsed: computed(() => !props.block?.hasVisibilityCondition()),
		searchKeyWords:
			"Condition, Visibility, VisibilityCondition, Visibility Condition, show, hide, display, hideIf, showIf",
	},
	attributes: {
		collapsed: computed(() => isObjectEmpty(blockController.getAttributes())),
		searchKeyWords: "Attributes, CustomAttributes, Custom Attributes, HTML Attributes, Data Attributes",
	},
}

const filteredSections = computed(() =>
	Object.keys(sections).filter((sectionName) => {
		const condition = sections[sectionName]?.condition
		return !condition || condition.value
	}),
)
</script>
