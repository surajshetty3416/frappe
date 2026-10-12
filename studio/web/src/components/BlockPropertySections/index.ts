import accessibilitySection from "@builder/components/BlockPropertySections/AccessibilitySection";
import collectionOptionsSection from "@builder/components/BlockPropertySections/CollectionOptionsSection";
import customAttributesSection from "@builder/components/BlockPropertySections/CustomAttributesSection";
import dataKeySection from "@builder/components/BlockPropertySections/DataKeySection";
import dimensionSection from "@builder/components/BlockPropertySections/DimensionSection";
import editorConfigSection from "@builder/components/BlockPropertySections/EditorConfigSection";
import HTMLOptionsSection from "@builder/components/BlockPropertySections/HTMLOptionsSection";
import imageOptionsSection from "@builder/components/BlockPropertySections/ImageOptionsSection";
import inputOptionsSection from "@builder/components/BlockPropertySections/InputOptionsSection";
import layoutSection from "@builder/components/BlockPropertySections/LayoutSection";
import linkSection from "@builder/components/BlockPropertySections/LinkSection";
import moreStylesSection from "@builder/components/BlockPropertySections/MoreStylesSection";
import optionsSection from "@builder/components/BlockPropertySections/OptionsSection";
import positionSection from "@builder/components/BlockPropertySections/PositionSection";
import spacingSection from "@builder/components/BlockPropertySections/SpacingSection";
import standardPropsInputSection from "@builder/components/BlockPropertySections/StandardPropsInputSection";
import styleSection from "@builder/components/BlockPropertySections/StyleSection";
import transitionSection from "@builder/components/BlockPropertySections/TransitionSection";
import typographySection from "@builder/components/BlockPropertySections/TypographySection";
import videoOptionsSection from "@builder/components/BlockPropertySections/VideoOptionsSection";
import { createRegistry, type RegistryItem } from "@builder/utils/createRegistry";
import type { Component, ComputedRef } from "vue";

export type BlockProperty = {
	component: Component;
	getProps?: () => Record<string, unknown>;
	events?: Record<string, unknown>;
	searchKeyWords: string;
	condition?: () => boolean;
	innerText?: string;
	usedStyleProperties?: string[];
};

export type PropertySection = RegistryItem & {
	properties: BlockProperty[] | (() => BlockProperty[]);
	collapsed?: boolean | ComputedRef<boolean>;
};

export const propertySections = createRegistry<PropertySection>();

const sections = [
	standardPropsInputSection,
	collectionOptionsSection,
	linkSection,
	layoutSection,
	imageOptionsSection,
	HTMLOptionsSection,
	videoOptionsSection,
	inputOptionsSection,
	typographySection,
	styleSection,
	dimensionSection,
	spacingSection,
	transitionSection,
	optionsSection,
	positionSection,
	dataKeySection,
	accessibilitySection,
	customAttributesSection,
	editorConfigSection,
	moreStylesSection,
] as PropertySection[];

// registered at module load: stylePropertiesWithControls reads the registry
// before the property panel mounts
sections.forEach(propertySections.register);
