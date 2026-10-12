import MainMenu from "@web/components/MainMenu.vue";
import PublishButton from "@web/components/PublishButton.vue";
import ModeSwitcher from "@web/components/ToolbarItems/ModeSwitcher.vue";
import PageTitlePopover from "@web/components/ToolbarItems/PageTitlePopover.vue";
import ReadOnlyBadge from "@web/components/ToolbarItems/ReadOnlyBadge.vue";
import ToolbarActions from "@web/components/ToolbarItems/ToolbarActions.vue";
import ViewerAvatars from "@web/components/ToolbarItems/ViewerAvatars.vue";
import useBuilderStore from "@web/stores/builderStore";
import usePageStore from "@web/stores/pageStore";
import { createRegistry, type RegistryItem } from "@web/utils/createRegistry";
import type { Component } from "vue";

export type ToolbarRegion = "left" | "center" | "right";

export type ToolbarItem = RegistryItem & {
	region: ToolbarRegion;
	component: Component;
	props?: () => Record<string, unknown>;
};

export const toolbarItems = createRegistry<ToolbarItem>();

// the route chunk imports this after pinia is installed, so the lookups resolve
const builderStore = useBuilderStore();
const pageStore = usePageStore();

toolbarItems.register({ name: "menu", region: "left", component: MainMenu });
toolbarItems.register({ name: "modes", region: "left", component: ModeSwitcher });
toolbarItems.register({ name: "page", region: "center", component: PageTitlePopover });

toolbarItems.register({
	name: "viewers",
	region: "right",
	component: ViewerAvatars,
	condition: () => builderStore.viewers.length > 0,
});

toolbarItems.register({
	name: "read-only",
	region: "right",
	component: ReadOnlyBadge,
	condition: () => builderStore.readOnlyMode,
});

// one item, not five: the icons share a gap-2 group inside a gap-4 region
toolbarItems.register({ name: "actions", region: "right", component: ToolbarActions });

toolbarItems.register({
	name: "publish",
	region: "right",
	component: PublishButton,
	props: () => ({ disabled: builderStore.readOnlyMode }),
	condition: () => !(builderStore.readOnlyMode && pageStore.activePage?.is_template),
});
