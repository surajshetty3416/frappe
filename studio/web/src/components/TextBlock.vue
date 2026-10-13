<template>
	<component :is="block.getTag()" ref="component" class="__text_block__">
		<div
			class="__text_content__ bg-clip-[inherit] bg-inherit [-webkit-background-clip:inherit] [background-image:inherit]"
			v-html="textContent"
			v-show="textContent"></div>
		<slot />
	</component>
</template>

<script setup lang="ts">
import type Block from "@web/block";
import { BlockValueResolver } from "@web/utils/blockValueResolver";
import { setFontFromHTML } from "@web/utils/fontManager";
import { Ref, computed, onBeforeMount, ref } from "vue";

const component = ref(null) as Ref<HTMLElement | null>;

const props = withDefaults(
	defineProps<{
		block: Block;
		data?: Record<string, any>;
		componentData?: Record<string, any> | null;
		defaultProps?: Record<string, any> | null;
		breakpoint?: string;
	}>(),
	{
		data: () => ({}),
		componentData: null,
		defaultProps: null,
		breakpoint: "desktop",
	},
);

const valueResolver = new BlockValueResolver({
	block: () => props.block,
	data: () => props.data ?? null,
	componentData: () => props.componentData ?? null,
	defaultProps: () => props.defaultProps ?? null,
});

const textContent = computed(() => {
	const dynamicContent = valueResolver.applyDynamicValues("key", { innerHTML: null }).innerHTML;
	return String(dynamicContent || props.block.getInnerHTML() || "");
});

onBeforeMount(() => setFontFromHTML(props.block.getInnerHTML() || ""));

defineExpose({ component });
</script>
<style scoped>
/* no box — a block box inside inline tags (span/a) fragments their background/radius */
.__text_content__ {
	display: contents;
}
</style>
