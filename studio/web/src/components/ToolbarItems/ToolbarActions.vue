<template>
	<div class="flex items-center gap-2">
		<span class="text-sm text-ink-gray-3" v-if="pageStore.savingPage && pageStore.activePage?.is_template">
			{{ __("Saving template") }}
		</span>
		<ComponentUpdates />
		<Tooltip v-if="hasVersionHistory" :text="__('Version History')" :hoverDelay="600" :offset="12">
			<Button
				:variant="builderStore.showVersionHistory ? 'subtle' : 'ghost'"
				icon="lucide-history"
				:disabled="builderStore.readOnlyMode"
				@click="toggleVersionHistory"></Button>
		</Tooltip>
		<Tooltip :text="__('Settings')" :hoverDelay="600" :offset="12">
			<Button variant="ghost" @click="openSettings" :icon="SettingsGearIcon"></Button>
		</Tooltip>
		<Tooltip :text="__('Preview')" :hoverDelay="0.6" arrow-class="mb-3">
			<Button variant="ghost" :icon="PlayIcon" :label="__('Preview')" @click="openPreview"></Button>
		</Tooltip>
	</div>
</template>
<script setup lang="ts">
import { __ } from "@web/translation";
import ComponentUpdates from "@web/components/ComponentUpdates.vue";
import PlayIcon from "@web/components/Icons/Play.vue";
import SettingsGearIcon from "@web/components/Icons/SettingsGear.vue";
import useBuilderStore from "@web/stores/builderStore";
import useCanvasStore from "@web/stores/canvasStore";
import usePageStore from "@web/stores/pageStore";
import { Tooltip } from "frappe-ui";
import { computed } from "vue";

const builderStore = useBuilderStore();
const canvasStore = useCanvasStore();
const pageStore = usePageStore();

// history is page-level: none while editing a component in place or on a template page
const hasVersionHistory = computed(
	() => canvasStore.editingMode !== "fragment" && !pageStore.activePage?.is_template,
);

const toggleVersionHistory = () => {
	builderStore.showRightPanel = true;
	builderStore.showVersionHistory = !builderStore.showVersionHistory;
};

const openSettings = (e: MouseEvent) => {
	(e.currentTarget as HTMLElement)?.blur();
	builderStore.showSettingsDialog = true;
};

const openPreview = () => pageStore.openPreview(pageStore.selectedPage as string);
</script>
