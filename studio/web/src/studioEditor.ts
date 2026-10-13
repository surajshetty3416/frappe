// Builder Page in Studio's editor shell: Builder's canvas as the preview, and the shell's
// contract answered from Builder's stores.
import type Block from "@web/block";
import BuilderCanvas from "@web/components/BuilderCanvas.vue";
import { webPages } from "@web/data/webPage";
import useBuilderStore from "@web/stores/builderStore";
import useCanvasStore from "@web/stores/canvasStore";
import usePageStore from "@web/stores/pageStore";
import type { BuilderPage } from "@web/types/doctypes";
import { getCopyWithoutParent, getRootBlockTemplate } from "@web/utils/helpers";
import { useDebounceFn, useResizeObserver } from "@vueuse/core";
import { defineArtifactEditor, type ElementProperty } from "@shell/editor";
import { LoadingIndicator, toast } from "frappe-ui";
import { computed, defineComponent, h, nextTick, provide, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

const PAD = 24;
let host: HTMLElement | null = null;

// the canvas is the editor's; in the shell it shows the page and nothing of Builder's chrome
const style = document.createElement("style");
style.textContent = `
[data-studio-preview] [data-builder-canvas] > div.fixed > div:not(.canvas),
[data-studio-preview] [data-builder-canvas] .canvas > div:not(.__builder_component__),
[data-studio-preview] [data-builder-canvas] > div.bottom-12,
[data-studio-preview] [data-builder-canvas] > div.grid.place-items-center,
[data-studio-preview] [data-builder-canvas] > .overlay { display: none !important; }
[data-studio-preview] [data-builder-canvas] .canvas { box-shadow: 0 0 0 1px var(--outline-gray-2); border-radius: 2px; }
`;
document.head.appendChild(style);

const BuilderPagePreview = defineComponent({
	name: "BuilderPagePreview",
	setup() {
		const route = useRoute();
		const router = useRouter();
		const pageStore = usePageStore();
		const canvasStore = useCanvasStore();
		const canvas = ref<InstanceType<typeof BuilderCanvas> | null>(null);
		const root = ref<HTMLElement | null>(null);
		const minHeight = ref(0);
		const fitted = ref(false);

		provide("pageCanvas", canvas);
		provide("fragmentCanvas", ref(null));
		watch(canvas, (value) => {
			canvasStore.activeCanvas = value;
			canvasStore.editingMode = "page";
			fitSoon();
		});
		watch(root, (value) => (host = value));

		async function open(pageId: unknown) {
			if (typeof pageId !== "string" || !pageId) return;
			if (pageId === "new") return createPage();
			if (pageId === pageStore.selectedPage && pageStore.pageBlocks.length) return fitSoon();
			fitted.value = false;
			await pageStore.setPage(pageId, true, route.query);
		}
		watch(() => route.params.pageId, open, { immediate: true });
		watch(
			() => pageStore.settingPage,
			(setting) => !setting && fitSoon(),
		);

		async function createPage() {
			const page = (await webPages.insert.submit({
				page_title: "Untitled page",
				draft_blocks: [getRootBlockTemplate()],
			} as unknown as BuilderPage)) as BuilderPage;
			router.replace({ name: "builder-editor", params: { pageId: page.name }, query: route.query });
		}

		// the page's desktop width fills the panel, top first, like a document
		async function fit() {
			const room = root.value;
			const props = canvas.value?.canvasProps;
			if (!room || !props) return;
			const desktop = props.breakpoints.find((breakpoint) => breakpoint.device === "desktop");
			const scale = Math.min(1, (room.clientWidth - PAD * 2) / (desktop?.width || 1400));
			props.scale = scale;
			props.translateX = 0;
			props.translateY = 0;
			minHeight.value = (room.clientHeight - PAD * 2) / scale;
			await nextTick();
			const page = room.querySelector(".canvas");
			if (!page) return;
			props.translateY = (room.getBoundingClientRect().top + PAD - page.getBoundingClientRect().top) / scale;
			fitted.value = true;
		}
		// Builder fits its own way first, as the page loads; this runs after it
		const fitSoon = () => requestAnimationFrame(() => requestAnimationFrame(() => fit()));
		useResizeObserver(root, useDebounceFn(fit, 50));

		return () =>
			h(
				"div",
				// the canvas is position: fixed; paint containment keeps it inside the panel
				{ ref: root, "data-studio-preview": "", class: "relative h-full overflow-hidden bg-surface-gray-2", style: { contain: "paint" } },
				[
					pageStore.pageBlocks[0]
						? h(BuilderCanvas, {
								ref: canvas,
								blockData: pageStore.pageBlocks[0],
								canvasStyles: { minHeight: `${minHeight.value}px` },
								class: [
									"canvas-container absolute inset-0 flex justify-center overflow-hidden transition-opacity duration-150",
									fitted.value && !pageStore.settingPage ? "opacity-100" : "opacity-0",
								],
							})
						: null,
					!fitted.value || pageStore.settingPage
						? h("div", { class: "absolute inset-0 grid place-items-center" }, [
								h(LoadingIndicator, { class: "size-5 text-ink-gray-4" }),
							])
						: null,
				],
			);
	},
});

const findBlock = (id: string) => (useCanvasStore().activeCanvas?.findBlock(id) as Block | null) ?? null;
const blockNode = (id: string) =>
	host?.querySelector<HTMLElement>(
		`.canvas[data-breakpoint="desktop"] .__builder_component__[data-block-id="${CSS.escape(id)}"]`,
	) ?? null;

const save = useDebounceFn(() => usePageStore().savePage(), 300);

function kind(block: Block) {
	if (block.isRoot()) return { label: "Page", icon: "lucide-file" };
	if (block.isHeader()) return { label: "Heading", icon: "lucide-heading" };
	if (block.isButton()) return { label: "Button", icon: "lucide-mouse-pointer-click" };
	if (block.isLink()) return { label: "Link", icon: "lucide-link" };
	if (block.isImage()) return { label: "Image", icon: "lucide-image" };
	if (block.isRepeater()) return { label: "Repeater", icon: "lucide-repeat" };
	if (block.isSVG()) return { label: "Graphic", icon: "lucide-shapes" };
	if (block.isHTML()) return { label: "HTML", icon: "lucide-code-xml" };
	if (block.isText()) return { label: "Text", icon: "lucide-type" };
	return { label: "Container", icon: "lucide-square-dashed" };
}
const DEFAULT_NAMES = new Set(["body", "container", "text", "image", "button", "link", "html", "repeater", "section"]);
const hasText = (block: Block) => block.isText() || block.isLink() || block.isButton();

const sizes = (values: number[], unit = "px") => values.map((value) => ({ label: `${value}`, value: `${value}${unit}` }));
const SPACING = sizes([0, 4, 8, 12, 16, 24, 32, 48, 64, 96]);
const RADIUS = [...sizes([0, 4, 8, 12, 16, 24]), { label: "Full", value: "9999px" }];

function property(block: Block, name: string, label: string, icon: string, type: "color" | "select", options?: { label: string; value: string }[]): ElementProperty {
	let value = String(block.getStyle(name as styleProperty) ?? "");
	// an inherited value shows as what the page renders
	if (!value) {
		const node = blockNode(block.blockId);
		const rendered = node ? getComputedStyle(node).getPropertyValue(name.replace(/[A-Z]/g, (c) => `-${c.toLowerCase()}`)) : "";
		if (type === "color" || options?.some((option) => option.value === rendered)) value = rendered;
	}
	return {
		name,
		label,
		icon,
		type,
		// a value outside the list still shows, as itself
		options: options && value && !options.some((option) => option.value === value) ? [{ label: value, value }, ...options] : options,
		value,
		set(next: string) {
			block.setStyle(name as styleProperty, next);
			save();
		},
	};
}

function blockProperties(block: Block): ElementProperty[] {
	if (hasText(block)) {
		return [
			property(block, "fontSize", "Size", "lucide-a-large-small", "select", sizes([12, 14, 16, 18, 20, 24, 30, 36, 48, 60, 72])),
			property(block, "fontWeight", "Weight", "lucide-bold", "select", [
				{ label: "Regular", value: "400" },
				{ label: "Medium", value: "500" },
				{ label: "Semibold", value: "600" },
				{ label: "Bold", value: "700" },
			]),
			property(block, "textAlign", "Align", "lucide-align-left", "select", [
				{ label: "Left", value: "left" },
				{ label: "Center", value: "center" },
				{ label: "Right", value: "right" },
			]),
			property(block, "color", "Color", "lucide-palette", "color"),
		];
	}
	if (block.isImage()) {
		return [
			property(block, "objectFit", "Fit", "lucide-scan", "select", [
				{ label: "Cover", value: "cover" },
				{ label: "Contain", value: "contain" },
			]),
			property(block, "borderRadius", "Corners", "lucide-square-round-corner", "select", RADIUS),
		];
	}
	return [
		property(block, "background", "Background", "lucide-paint-bucket", "color"),
		property(block, "padding", "Padding", "lucide-square-dashed", "select", SPACING),
		property(block, "gap", "Gap", "lucide-between-horizontal-start", "select", SPACING),
		property(block, "borderRadius", "Corners", "lucide-square-round-corner", "select", RADIUS),
	];
}

const page = computed(() => usePageStore().activePage);

export default defineArtifactEditor({
	preview: BuilderPagePreview,

	title: () => page.value?.page_title || "Untitled page",
	rename: (title) => usePageStore().updateActivePage("page_title", title) as Promise<unknown>,
	status() {
		if (usePageStore().savingPage) return { label: "Saving…", theme: "gray" };
		if (!page.value?.published) return { label: "Draft", theme: "gray" };
		if (page.value.draft_blocks) return { label: "Unpublished changes", theme: "orange" };
		return { label: "Published", theme: "green" };
	},
	primaryAction() {
		const live = page.value?.published && !page.value.draft_blocks;
		return {
			label: live ? "Published" : "Publish",
			icon: live ? "lucide-check" : undefined,
			disabled: Boolean(live) || useBuilderStore().readOnlyMode,
			run: async () => {
				await usePageStore().publishPage(false);
				toast.success("Published");
			},
		};
	},
	details() {
		const route = page.value?.route;
		if (!route) return [];
		const path = `/${route.replace(/^\//, "")}`;
		return [{ label: "Address", value: path, href: page.value?.published ? path : undefined }];
	},
	code() {
		const root = useCanvasStore().activeCanvas?.getRootBlock();
		return { language: "json", content: root ? JSON.stringify([getCopyWithoutParent(root)], null, 2) : "" };
	},
	async reload(modified) {
		const pageStore = usePageStore();
		if (!pageStore.selectedPage) return;
		if (pageStore.savingPage) await pageStore.waitTillPageIsSaved();
		// the save this tab made itself
		if (modified && modified === pageStore.activePage?.modified) return;
		await pageStore.setPage(pageStore.selectedPage, false);
	},

	elementAt(node) {
		const element = node.closest<HTMLElement>(".__builder_component__[data-block-id]");
		if (!element || !host?.contains(element)) return null;
		const block = findBlock(element.dataset.blockId as string);
		if (!block) return null;
		const name = block.blockName && !DEFAULT_NAMES.has(block.blockName) ? block.blockName : null;
		const { label, icon } = kind(block);
		return { id: block.blockId, label: name ?? label, icon, hasText: hasText(block) };
	},
	elementRect: (id) => blockNode(id)?.getBoundingClientRect() ?? null,
	textNode: (id) => blockNode(id)?.querySelector<HTMLElement>(":scope > .__text_content__") ?? null,
	setText(id, html) {
		findBlock(id)?.setInnerHTML(html);
		save();
	},
	properties(id) {
		const block = findBlock(id);
		return block ? blockProperties(block) : [];
	},
});
