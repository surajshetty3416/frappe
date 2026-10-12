import MoreStylesPanel from "@builder/components/MoreStylesPanel.vue";
import blockController from "@builder/utils/blockController";
import { getStylePropertiesWithoutControls } from "@builder/utils/stylePropertiesWithControls";
import { computed } from "vue";
import { __ } from "@builder/translation";

const moreStylesSectionProperties = [
	{
		component: MoreStylesPanel,
		searchKeyWords: "More, Styles, CSS, Property, Properties, Advanced",
	},
];

export default {
	name: __("More Styles"),
	properties: moreStylesSectionProperties,
	collapsed: computed(() => {
		const block = blockController.getFirstSelectedBlock();
		if (!block) return true;
		const styles = { ...block.baseStyles, ...block.tabletStyles, ...block.mobileStyles };
		return getStylePropertiesWithoutControls(styles).size === 0;
	}),
	condition: () => blockController.getSelectedBlocks().length === 1,
};
