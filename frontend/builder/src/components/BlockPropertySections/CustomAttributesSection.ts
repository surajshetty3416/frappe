import ObjectEditor from "@builder/components/ObjectEditor.vue";
import blockController from "@builder/utils/blockController";
import { computed } from "vue";
import { __ } from "@builder/translation";

const customAttributesSectionProperties = [
	{
		component: ObjectEditor,
		getProps: () => {
			return {
				obj: blockController.getCustomAttributes() as Record<string, string>,
				allowDynamicValues: true,
			};
		},
		searchKeyWords: "Attributes, CustomAttributes, Custom Attributes, HTML Attributes, Data Attributes",
		events: {
			"update:obj": (obj: Record<string, string>) => blockController.setCustomAttributes(obj),
		},
	},
];

export default {
	name: __("HTML Attributes"),
	properties: customAttributesSectionProperties,
	collapsed: computed(() => {
		return Object.keys(blockController.getCustomAttributes()).length === 0;
	}),
};
