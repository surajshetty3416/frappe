<template>
	<div class="flex h-screen">
		<DashboardSidebar></DashboardSidebar>
		<div class="flex w-full flex-1 flex-col overflow-hidden">
			<DashboardToolbar class="sticky top-0" />
			<DashboardHead />
			<DashboardContent />
		</div>
	</div>
	<BuilderCommandPalette />
	<TemplatesDialog />
</template>
<script setup lang="ts">
import BuilderCommandPalette from "@builder/components/BuilderCommandPalette.vue";
import DashboardContent from "@builder/components/DashboardContent.vue";
import DashboardHead from "@builder/components/DashboardHead.vue";
import DashboardSidebar from "@builder/components/DashboardSidebar.vue";
import DashboardToolbar from "@builder/components/DashboardToolbar.vue";
import TemplatesDialog from "@builder/components/Templates/TemplatesDialog.vue";
import { builderSettings } from "@builder/data/builderSettings";
import router, { sessionUser } from "@builder/router";
import { prefetchBuilderSettings, prefetchTemplateGallery } from "@builder/utils/prefetch";
import { useTelemetry } from "@framework/ui/telemetry";
import { onMounted, watch } from "vue";

const telemetry = useTelemetry();

onMounted(() => {
	prefetchBuilderSettings();
	prefetchTemplateGallery();
});
// Dev benches have telemetry (and thus the survey) off; ?persona_survey=test forces the redirect.
const devForceShow = new URLSearchParams(window.location.search).get("persona_survey") === "test";

watch(
	[() => telemetry.isEnabled, () => builderSettings.doc, sessionUser],
	() => {
		if (!telemetry.isEnabled && !devForceShow) return;
		if (!builderSettings.doc) return;
		if (builderSettings.doc.persona_survey_done && !devForceShow) return;
		if (!sessionUser.value || sessionUser.value === "Guest") return;
		router.replace({
			name: "persona-survey",
			query: devForceShow ? { persona_survey: "test" } : {},
		});
	},
	{ immediate: true },
);
</script>
