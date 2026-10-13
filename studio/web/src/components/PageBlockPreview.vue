<template>
	<div ref="component" class="!relative" v-html="html"></div>
</template>
<script setup lang="ts">
// A form or chat block as the published page renders it, from the server's own markup. The
// overlay keeps clicks on the canvas, so the block selects instead of its inputs taking focus.
import type Block from "@web/block";
import { createResource } from "frappe-ui";
import { computed, ref, watch } from "vue";

const STYLE_ID = "fb-page-blocks";

const props = defineProps<{ block: Block }>();
const component = ref<HTMLElement | null>(null);

const preview = createResource({
	url: "frappe.web.page_blocks.preview",
	makeParams: () => ({
		block: { blockId: props.block.blockId, form: props.block.form, chat: props.block.chat },
	}),
	onSuccess(data: { css: string }) {
		if (document.getElementById(STYLE_ID)) return;
		const style = document.createElement("style");
		style.id = STYLE_ID;
		style.textContent = data.css;
		document.head.appendChild(style);
	},
});
watch(() => JSON.stringify([props.block.form, props.block.chat]), () => preview.reload(), { immediate: true });

const html = computed(
	() => `<div class="absolute inset-0 z-10"></div>${(preview.data as { html?: string } | null)?.html ?? ""}`,
);

defineExpose({ component });
</script>
