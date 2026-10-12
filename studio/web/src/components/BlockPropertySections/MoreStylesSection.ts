import MoreStylesPanel from "@web/components/MoreStylesPanel.vue";
import blockController from "@web/utils/blockController";
import { getStylePropertiesWithoutControls } from "@web/utils/stylePropertiesWithControls";
import { computed } from "vue";
import { __ } from "@web/translation";

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
