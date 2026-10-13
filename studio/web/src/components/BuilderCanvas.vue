<template>
	<div ref="canvasContainer" :data-builder-canvas="canvasId" class="h-full overflow-y-auto overflow-x-hidden">
		<component :is="'style'" v-if="pageStyles" v-text="pageStyles" />
		<component :is="'style'" v-if="blockClientStyles" v-text="blockClientStyles" />
		<div
			class="canvas relative min-h-full bg-white"
			:style="{ width: `${frameWidth}px`, zoom: scale }"
			:data-breakpoint="activeBreakpoint">
			<BuilderBlock
				class="min-h-[inherit]"
				:block="block"
				:style="cssVariables"
				:key="block.blockId"
				:breakpoint="activeBreakpoint"
				:data="pageStore.pageData" />
		</div>
	</div>
</template>
<script setup lang="ts">
import type Block from "@web/block";
import { builderSettings } from "@web/data/builderSettings";
import usePageStore from "@web/stores/pageStore";
import { findBlockInTree } from "@web/utils/block/tree";
import { setFont } from "@web/utils/fontManager";
import {
	type BlockClientScriptRuntime,
	executeClientScriptRestricted,
	executeClientScriptUnrestricted,
} from "@web/utils/scriptSandbox";
import { useBuilderToken } from "@web/utils/useBuilderToken";
import { useElementSize } from "@vueuse/core";
import { Ref, computed, provide, reactive, ref, useId, watchEffect } from "vue";
import BuilderBlock from "./BuilderBlock.vue";

const pageStore = usePageStore();
const canvasId = `builder-canvas-${useId()}`;

const props = defineProps<{ blockData: Block }>();

const { cssVariables, fontTokens } = useBuilderToken();
// blocks reference font tokens as var(--id), which never reaches the font loader
watchEffect(() => fontTokens.value.forEach((token: any) => setFont(token.value)));

const canvasContainer = ref(null) as Ref<HTMLElement | null>;
const block = ref(props.blockData) as Ref<Block>;
// the preview shows the base styles every breakpoint inherits
const activeBreakpoint = ref("desktop");
// desktop lays out at its own width and zooms to fit the panel, so a narrow panel never reflows the page
const DESKTOP_WIDTH = 1280;
const { width: panelWidth } = useElementSize(canvasContainer);
const frameWidth = computed(() => Math.max(DESKTOP_WIDTH, panelWidth.value));
const scale = computed(() => (panelWidth.value ? panelWidth.value / frameWidth.value : 1));

// the page's own CSS, from its head and its CSS scripts, held to this canvas
const pageStyles = computed(() => {
	const head = pageStore.activePage?.head_html || "";
	const css = [
		...Array.from(new DOMParser().parseFromString(head, "text/html").querySelectorAll("style"), (style) => style.textContent),
		...pageStore.activePageScripts.filter((script) => script.script_type === "CSS").map((script) => script.script),
	].join("\n");
	return css.trim() ? `@scope ([data-builder-canvas="${canvasId}"]) { ${css} }` : "";
});
const blockStyles = reactive(new Map<string, string>());
const blockClientStyles = computed(() => Array.from(blockStyles.values()).join("\n"));

const getRootBlock = () => block.value;
const setRootBlock = (newBlock: Block) => (block.value = newBlock);
const findBlock = (blockId: string) => findBlockInTree(blockId, [block.value]);

function emulateBlockClientScript(script: BlockClientScriptRuntime) {
	const key = `${script.key}:${script.breakpoint}`;
	const escape = (value: string) => value.replaceAll("\\", "\\\\").replaceAll('"', '\\"');
	const selector = `[data-builder-canvas="${canvasId}"] [data-block-uid="${escape(script.key)}"][data-breakpoint="${escape(script.breakpoint)}"]`;
	blockStyles.set(key, script.css ? `@scope (${selector}) { ${script.css} }` : "");

	const mode = builderSettings.doc?.execute_block_scripts_in_editor ?? "Restricted";
	let cleanup = () => {};
	if (mode !== "Don't Execute" && script.javascript.trim()) {
		const context = { componentData: script.componentData, props: script.props };
		cleanup =
			mode === "Unrestricted"
				? executeClientScriptUnrestricted(script.element, script.javascript, context)
				: executeClientScriptRestricted(script.element, canvasContainer.value, script.javascript, context);
	}
	return () => {
		try {
			cleanup();
		} finally {
			blockStyles.delete(key);
		}
	};
}
provide("emulateBlockClientScript", emulateBlockClientScript);

defineExpose({ block, getRootBlock, setRootBlock, findBlock, activeBreakpoint });
</script>
<style>
.canvas p:not(:where(.prose, .ProseMirror) *) {
	line-height: revert;
}
</style>
