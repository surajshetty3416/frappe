<template>
	<component
		:is="getComponentName(block)"
		:data-block-id="block.blockId"
		:data-block-uid="uidToUse"
		:data-breakpoint="breakpoint"
		:class="classes"
		v-bind="attributes"
		:style="styles"
		ref="component">
		<template v-if="optionText != null">{{ optionText }}</template>
		<BuilderBlock
			:data="data"
			:componentData="resolvedComponentData"
			:defaultProps="defaultProps"
			:block="child"
			:breakpoint="breakpoint"
			:isChildOfComponent="block.isExtendedFromComponent() || isChildOfComponent"
			:key="child.blockId"
			:repeater-index="repeaterIndex"
			v-for="child in block.getChildren()" />
	</component>
</template>
<script setup lang="ts">
import type Block from "@web/block";
import { builderSettings } from "@web/data/builderSettings";
import useComponentStore from "@web/stores/componentStore";
import usePageStore from "@web/stores/pageStore";
import { BlockValueResolver } from "@web/utils/blockValueResolver";
import { needsItalic, setFont } from "@web/utils/fontManager";
import { extractComponentId, getTextContent } from "@web/utils/helpers";
import type { BlockClientScriptEmulator } from "@web/utils/scriptSandbox";
import {
	computed,
	inject,
	nextTick,
	onMounted,
	onUnmounted,
	ref,
	useAttrs,
	watch,
	watchEffect,
} from "vue";
import BlockHTML from "./BlockHTML.vue";
import DataLoaderBlock from "./DataLoaderBlock.vue";
import PageBlockPreview from "./PageBlockPreview.vue";
import TextBlock from "./TextBlock.vue";

const componentStore = useComponentStore();
const component = ref<HTMLElement | InstanceType<typeof TextBlock> | null>(null);
const attrs = useAttrs();
const isMounted = ref(false);

const pageStore = usePageStore();

const props = withDefaults(
	defineProps<{
		block: Block;
		isChildOfComponent?: boolean;
		breakpoint?: string;
		data?: Record<string, any> | null;
		componentData?: Record<string, any> | null;
		defaultProps?: Record<string, any> | null;
		repeaterIndex?: string | number | null;
	}>(),
	{
		isChildOfComponent: false,
		breakpoint: "desktop",
		data: null,
		componentData: null,
		defaultProps: null,
		repeaterIndex: null,
	},
);

const resolvedComponentData = computed(() => {
	const componentId = extractComponentId(props.block);
	if (componentId) {
		return componentStore.getComponentInstanceData(componentId, uidToUse);
	} else {
		return props.componentData;
	}
});

defineOptions({
	inheritAttrs: false,
});

// For repeater items the same Block object is rendered multiple times,
// so we need a unique identifier per rendered instance (used by client scripts)
const uidToUse = !!props.repeaterIndex
	? `builder-block-${props.block.blockId}-${props.repeaterIndex}`
	: props.block.blockId;

const getComponentName = (block: Block) => {
	if (block.form || block.chat) {
		return PageBlockPreview;
	}
	if (block.isRepeater()) {
		return DataLoaderBlock;
	}
	if (block.isInlineSVG()) {
		return BlockHTML;
	}
	if (block.isText() || block.isLink() || block.isButton()) {
		return TextBlock;
	} else if (block.isHTML()) {
		return BlockHTML;
	} else {
		return block.getTag();
	}
};

const classes = computed(() => {
	return [
		attrs.class,
		"__builder_component__",
		"outline-none",
		"select-none",
		...props.block.getClasses(),
		hiddenDueToVisibilityCondition.value ? "opacity-10" : "",
	];
});

const valueResolver = new BlockValueResolver({
	block: () => props.block,
	data: () => props.data ?? null,
	componentData: () => resolvedComponentData.value ?? null,
	defaultProps: () => props.defaultProps ?? null,
});

// option supports only text content, so its label renders as a text node instead of going through TextBlock
const optionText = computed(() => {
	if (props.block.getElement() !== "option") return null;
	const resolved = valueResolver.applyDynamicValues("key", { innerHTML: null }).innerHTML;
	return getTextContent(String(resolved ?? props.block.getInnerHTML() ?? ""));
});

const attributes = computed(() => {
	const RESTRICTED_ATTRIBS = ["data-block-id", "data-block-uid", "data-breakpoint"];
	let additionalAttributes: Record<string, any> = {};

	if (builderSettings.doc?.execute_block_scripts_in_editor !== "Don't Execute") {
		additionalAttributes = props.block.getCustomAttributes();
	}

	Object.keys(additionalAttributes).forEach((key) => {
		const trimmedKey = key.trim();
		if (RESTRICTED_ATTRIBS.includes(trimmedKey) || trimmedKey === "") {
			delete additionalAttributes[key];
		} else if (trimmedKey !== key) {
			additionalAttributes[trimmedKey] = additionalAttributes[key];
			delete additionalAttributes[key];
		}
	});

	const attribs = { ...additionalAttributes, ...props.block.getAttributes(), ...attrs } as {
		[key: string]: any;
	};

	if (props.block.isImage()) {
		if (attribs.darkSrc && !attribs.src) attribs.src = attribs.darkSrc;
		delete attribs.darkSrc;
	}

	if (
		props.block.form ||
		props.block.chat ||
		props.block.isText() ||
		props.block.isHTML() ||
		props.block.isInlineSVG() ||
		props.block.isLink() ||
		props.block.isButton() ||
		props.block.isRepeater()
	) {
		attribs.block = props.block;
		attribs.repeaterIndex = props.repeaterIndex;
		attribs.breakpoint = props.breakpoint;
		attribs.data = props.data;
		attribs.componentData = resolvedComponentData.value;
		attribs.defaultProps = props.defaultProps;
	}

	valueResolver.applyDynamicValues("attribute", attribs);

	if (props.block.isInput()) {
		attribs.readonly = true;
	}

	return attribs;
});

const emulateBlockClientScript = inject<BlockClientScriptEmulator>(
	"emulateBlockClientScript",
	() => () => {},
);

const target = computed(() => {
	if (!component.value) return null;
	if (component.value instanceof HTMLElement || component.value instanceof SVGElement) {
		return component.value;
	} else {
		return component.value.component;
	}
});

const styles = computed(() => {
	const dynamicStyles = valueResolver.applyDynamicValues("style", {}) as BlockStyleMap;

	const styleMap = {
		...props.block.getStyles(props.breakpoint),
		...props.block.getEditorStyles(),
		...dynamicStyles,
	} as BlockStyleMap;

	if (props.block.getTag() === "iframe") {
		styleMap.pointerEvents = "none";
	}

	// a family name's spaces are escaped, the commas between families are not
	if (styleMap.fontFamily && typeof styleMap.fontFamily === "string") {
		styleMap.fontFamily = styleMap.fontFamily
			.split(",")
			.map((family) => family.trim().replace(/^['"]|['"]$/g, "").replace(/ /g, "\\ "))
			.join(", ");
	}

	Object.keys(styleMap).forEach((key) => {
		if (key.startsWith("hover:")) delete styleMap[key];
	});

	return styleMap;
});

const emit = defineEmits(["mounted"]);

watchEffect(() => {
	const { block, breakpoint } = props;
	const italic = needsItalic(block.getStyle("fontStyle", breakpoint), block.getInnerHTML());
	let fontWeight = block.getStyle("fontWeight", breakpoint) as string;
	// italic faces are cut per weight, so they need the weight the text inherits
	if (italic && !fontWeight) fontWeight = block.getAncestorStyle("fontWeight", breakpoint) as string;
	let fontFamily = block.getStyle("fontFamily", breakpoint) as string;
	if (!fontFamily && (fontWeight || italic))
		fontFamily = block.getAncestorStyle("fontFamily", breakpoint) as string;
	setFont(fontFamily, fontWeight, italic);
});

onMounted(async () => {
	await nextTick();
	emit("mounted", target.value);

	isMounted.value = true;
});

onUnmounted(() => {
	const componentId = extractComponentId(props.block);
	if (componentId) {
		componentStore.deleteComponentData(componentId, uidToUse);
	}
});

const allResolvedProps = computed(() => {
	return valueResolver.getResolvedProps();
});

const fetchingComponentDetails = computed(() => {
	return (
		componentStore.fetchingComponentVersion.has(props.block.componentVersion || "") ||
		componentStore.fetchingComponent.has(props.block.extendedFromComponent || "")
	);
});
const componentDataReady = ref(false);

watch(
	[
		() => props.block.extendedFromComponent,
		() => props.block.componentVersion,
		() => props.componentData,
		() => uidToUse,
		fetchingComponentDetails,
		allResolvedProps,
	],
	([componentId, , , , fetchingComponentDetails, allResolvedProps]) => {
		componentDataReady.value = false;
		// can use extractComponentId but below code is more efficient
		if (!componentId) {
			return;
		}
		if (fetchingComponentDetails) {
			return;
		}
		componentStore.setComponentData(componentId, allResolvedProps, uidToUse, props.block.componentVersion);
	},
	{ immediate: true },
);

watch(resolvedComponentData, () => {
	componentDataReady.value = true;
});

const blockClientScript = computed(() => {
	const clientScript = props.block.extendedFromComponent
		? props.block.referenceComponent?.clientScript
		: props.block.clientScript;
	const javascript = clientScript?.js || "";
	const css = clientScript?.css || "";
	// null (not an empty object) so scriptless blocks skip canvas registration
	// and don't churn the shared blockStyles map into a render loop
	if (!javascript && !css) return null;
	return { javascript, css };
});

watch(
	[
		target,
		blockClientScript,
		resolvedComponentData,
		allResolvedProps,
		() => builderSettings.doc?.execute_block_scripts_in_editor,
		() => pageStore.settingPage,
		componentDataReady,
	],
	([element, clientScript, componentData, resolvedProps, , settingPage, dataReady], _, onCleanup) => {
		if (!element || !clientScript) return;
		const waitsForComponentData = Boolean(props.block.extendedFromComponent);
		const cleanup = emulateBlockClientScript({
			key: uidToUse,
			element: element as HTMLElement,
			breakpoint: props.breakpoint,
			css: clientScript.css ?? "",
			javascript:
				settingPage || (waitsForComponentData && !dataReady)
					? ""
					: (clientScript.javascript ?? ""),
			componentData: componentData ?? {},
			props: resolvedProps,
		});
		onCleanup(cleanup);
	},
	{ immediate: true },
);

const hiddenDueToVisibilityCondition = computed(() => {
	return valueResolver.isHiddenByVisibilityCondition();
});


</script>
