import accessibilitySection from "@web/components/BlockPropertySections/AccessibilitySection";
import collectionOptionsSection from "@web/components/BlockPropertySections/CollectionOptionsSection";
import customAttributesSection from "@web/components/BlockPropertySections/CustomAttributesSection";
import dataKeySection from "@web/components/BlockPropertySections/DataKeySection";
import dimensionSection from "@web/components/BlockPropertySections/DimensionSection";
import editorConfigSection from "@web/components/BlockPropertySections/EditorConfigSection";
import HTMLOptionsSection from "@web/components/BlockPropertySections/HTMLOptionsSection";
import imageOptionsSection from "@web/components/BlockPropertySections/ImageOptionsSection";
import inputOptionsSection from "@web/components/BlockPropertySections/InputOptionsSection";
import layoutSection from "@web/components/BlockPropertySections/LayoutSection";
import linkSection from "@web/components/BlockPropertySections/LinkSection";
import moreStylesSection from "@web/components/BlockPropertySections/MoreStylesSection";
import optionsSection from "@web/components/BlockPropertySections/OptionsSection";
import positionSection from "@web/components/BlockPropertySections/PositionSection";
import spacingSection from "@web/components/BlockPropertySections/SpacingSection";
import standardPropsInputSection from "@web/components/BlockPropertySections/StandardPropsInputSection";
import styleSection from "@web/components/BlockPropertySections/StyleSection";
import transitionSection from "@web/components/BlockPropertySections/TransitionSection";
import typographySection from "@web/components/BlockPropertySections/TypographySection";
import videoOptionsSection from "@web/components/BlockPropertySections/VideoOptionsSection";
import { createRegistry, type RegistryItem } from "@web/utils/createRegistry";
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
