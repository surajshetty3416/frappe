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
import { __ } from "@builder/translation";
import ComponentUpdates from "@builder/components/ComponentUpdates.vue";
import PlayIcon from "@builder/components/Icons/Play.vue";
import SettingsGearIcon from "@builder/components/Icons/SettingsGear.vue";
import useBuilderStore from "@builder/stores/builderStore";
import useCanvasStore from "@builder/stores/canvasStore";
import usePageStore from "@builder/stores/pageStore";
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
