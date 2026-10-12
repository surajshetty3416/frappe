<template>
	<div>
		<ContextMenu ref="contextMenu" :options="contextMenuOptions" :context="menuContext" />
		<NewBlockTemplate
			v-if="menuContext"
			:block="menuContext.block"
			v-model="builderStore.showBlockTemplateDialog"></NewBlockTemplate>
	</div>
</template>
<script setup lang="ts">
import type Block from "@web/block";
import { blockContextMenuOptions } from "@web/components/BlockContextMenuOptions";
import ContextMenu from "@web/components/ContextMenu.vue";
import NewBlockTemplate from "@web/components/Modals/NewBlockTemplate.vue";
import useBuilderStore from "@web/stores/builderStore";
import type { BlockMenuContext } from "@web/types/blockContextMenu";
import { Ref, ref } from "vue";

const builderStore = useBuilderStore();

// read all, not visible: each item applies its own condition to the context
const contextMenuOptions = blockContextMenuOptions.all;

const contextMenu = ref(null) as unknown as Ref<InstanceType<typeof ContextMenu>>;
const menuContext = ref(null) as unknown as Ref<BlockMenuContext>;

const showContextMenu = (event: MouseEvent, refBlock: Block) => {
	const target = event.target as HTMLElement;
	menuContext.value = {
		block: refBlock,
		target,
		fromLayersPanel: Boolean(target.closest(".block-layers")),
	};
	if (refBlock.isRoot()) return;
	contextMenu.value?.show(event);
};

const hideContextMenu = () => {
	contextMenu.value?.hide();
};

defineExpose({
	showContextMenu,
	hideContextMenu,
});
</script>
