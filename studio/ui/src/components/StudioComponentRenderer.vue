<template>
	<AppComponent v-if="block" :block="block" />
</template>

<script setup lang="ts">
import { provide, computed } from "vue"
import AppComponent from "@studio/components/AppComponent.vue"
import Block from "@studio/utils/block"
import useComponentStore from "@studio/stores/componentStore"

import { usePageScope } from "@studio/stores/codeStore"

const props = defineProps<{
	studioComponent: Block
	evaluationContext: Object
}>()
const componentStore = useComponentStore()
const pageScope = usePageScope()

const componentContext = computed(() => {
	const context = props.studioComponent?.getPropsAndAttributes() || {}
	const componentDoc = componentStore.getComponentDoc(props.studioComponent.componentName)
	if (componentDoc?.inputs) {
		componentDoc.inputs.forEach((input: any) => {
			if (!(input.input_name in context) && input.default !== undefined) {
				context[input.input_name] = input.default
			}

			Object.entries(context).forEach(([inputName, value]) => {
				context[inputName] = pageScope.evaluateDynamicValues(value, props.evaluationContext)
			})
		})
	}
	return { inputs: context }
})
provide("componentContext", componentContext)

const block = computed(() => componentStore.getNewStudioComponentInstance(props.studioComponent))
</script>
