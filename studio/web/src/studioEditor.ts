// Builder Page in Studio's editor shell: the page as the preview, and the shell's contract
// answered from the page store.
import type Block from "@web/block";
import BuilderCanvas from "@web/components/BuilderCanvas.vue";
import { webPages } from "@web/data/webPage";
import useCanvasStore from "@web/stores/canvasStore";
import usePageStore from "@web/stores/pageStore";
import type { BuilderPage } from "@web/types/doctypes";
import { getRootBlockTemplate } from "@web/utils/helpers";
import { useDebounceFn } from "@vueuse/core";
import { defineArtifactEditor, type ElementProperty } from "@shell/editor";
import { LoadingIndicator, createListResource, toast } from "frappe-ui";
import { computed, defineComponent, h, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

let host: HTMLElement | null = null;

const BuilderPagePreview = defineComponent({
	name: "BuilderPagePreview",
	setup() {
		const route = useRoute();
		const router = useRouter();
		const pageStore = usePageStore();
		const canvasStore = useCanvasStore();
		const canvas = ref<InstanceType<typeof BuilderCanvas> | null>(null);
		const root = ref<HTMLElement | null>(null);

		watch(canvas, (value) => (canvasStore.activeCanvas = value));
		watch(root, (value) => (host = value));

		async function open(pageId: unknown) {
			if (typeof pageId !== "string" || !pageId) return;
			if (pageId === "new") return createPage();
			if (pageId === pageStore.selectedPage && pageStore.pageBlocks.length) return;
			await pageStore.setPage(pageId, route.query);
		}
		watch(() => route.params.pageId, open, { immediate: true });

		async function createPage() {
			const page = (await webPages.insert.submit({
				page_title: "Untitled page",
				draft_blocks: [getRootBlockTemplate()],
			} as unknown as BuilderPage)) as BuilderPage;
			router.replace({ name: "builder-editor", params: { pageId: page.name }, query: route.query });
		}

		return () =>
			h("div", { ref: root, class: "relative h-full bg-surface-base" }, [
				pageStore.pageBlocks[0]
					? h(BuilderCanvas, {
							ref: canvas,
							blockData: pageStore.pageBlocks[0],
							class: ["transition-opacity duration-150", pageStore.settingPage ? "opacity-0" : "opacity-100"],
						})
					: null,
				pageStore.settingPage
					? h("div", { class: "absolute inset-0 grid place-items-center" }, [
							h(LoadingIndicator, { class: "size-5 text-ink-gray-4" }),
						])
					: null,
			]);
	},
});

const findBlock = (id: string) => (useCanvasStore().activeCanvas?.findBlock(id) as Block | null) ?? null;
const blockNode = (id: string) =>
	host?.querySelector<HTMLElement>(`.__builder_component__[data-block-id="${CSS.escape(id)}"]`) ?? null;

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

type Option = { label: string; value: string };

function select(
	name: string,
	label: string,
	icon: string,
	value: string,
	options: Option[],
	set: (value: string) => void,
): ElementProperty {
	return {
		name,
		label,
		icon,
		type: "select",
		value,
		// a value outside the list still shows, as itself
		options: value && !options.some((option) => option.value === value) ? [{ label: value, value }, ...options] : options,
		set(next) {
			set(next);
			save();
		},
	};
}

const NO_LINK = "none";
function linkProperty(block: Block) {
	const options = ((webPages.data ?? []) as BuilderPage[])
		.filter((page) => page.route && !/[<:]/.test(page.route))
		.map((page) => ({ label: page.page_title || page.route!, value: `/${page.route!.replace(/^\//, "")}` }));
	const href = String(block.getAttribute("href") ?? "");
	return select("link", "Link", "lucide-link", href, [{ label: "No link", value: NO_LINK }, ...options], (value) => {
		if (value === NO_LINK) return block.isLink() && block.unsetLink();
		if (!block.isLink()) block.convertToLink();
		block.setAttribute("href", value);
	});
}

const images = createListResource({
	doctype: "File",
	fields: ["file_name", "file_url"],
	filters: { is_folder: 0, file_type: ["in", ["PNG", "JPG", "JPEG", "SVG", "WEBP", "GIF"]] },
	orderBy: "creation desc",
	pageLength: 50,
	cache: "web-images",
});
function imageProperty(block: Block) {
	if (!images.fetched && !images.list.loading) images.fetch();
	const options = ((images.data ?? []) as { file_name: string; file_url: string }[]).map((file) => ({
		label: file.file_name,
		value: file.file_url,
	}));
	const src = String(block.getAttribute("src") ?? "");
	return select("image", "Image", "lucide-image", src, options, (value) => block.setAttribute("src", value));
}

function alignProperty(block: Block) {
	const node = blockNode(block.blockId);
	const value = String(block.getStyle("textAlign") || (node ? getComputedStyle(node).textAlign : ""));
	const options = [
		{ label: "Left", value: "left" },
		{ label: "Center", value: "center" },
		{ label: "Right", value: "right" },
	];
	// the browser reports an unset alignment as "start"
	const shown = value === "start" ? "left" : value;
	return select("align", "Align", "lucide-align-left", shown, options, (next) => block.setStyle("textAlign", next));
}

// a flag per breakpoint: desktop, tablet, phone
const VISIBILITY = [
	{ label: "Everywhere", value: "111" },
	{ label: "Desktop only", value: "100" },
	{ label: "Desktop and tablet", value: "110" },
	{ label: "Tablet and phone", value: "011" },
	{ label: "Phone only", value: "001" },
	{ label: "Hidden", value: "000" },
];
function visibilityProperty(block: Block) {
	const value = ["desktop", "tablet", "mobile"].map((breakpoint) => (block.isVisible(breakpoint) ? "1" : "0")).join("");
	return select("visibility", "Visibility", "lucide-eye", value, VISIBILITY, (next) => {
		const maps = [block.baseStyles, block.tabletStyles, block.mobileStyles];
		const shown = maps.map((styles) => styles.display).find((display) => display && display !== "none");
		next.split("").forEach((flag, index) => {
			const styles = maps[index];
			// a breakpoint that matches the one above inherits it
			if (index && flag === next[index - 1]) delete styles.display;
			else if (flag === "0") styles.display = "none";
			else if (shown || index) styles.display = shown || "flex";
			else delete styles.display;
		});
	});
}

function blockProperties(block: Block): ElementProperty[] {
	if (block.isRoot()) return [];
	return [
		linkProperty(block),
		...(block.isImage() ? [imageProperty(block)] : []),
		...(hasText(block) ? [alignProperty(block)] : []),
		visibilityProperty(block),
	];
}

function codeContent(page: BuilderPage) {
	const pageStore = usePageStore();
	const sections: [string, string | null | undefined][] = [
		["Data script", page.page_data_script],
		["Data", page.page_data_script ? JSON.stringify(pageStore.pageData, null, 2) : null],
		...pageStore.activePageScripts.map(
			(script) => [`Client script: ${script.name} (${script.script_type})`, script.script] as [string, string],
		),
		["Head HTML", page.head_html],
		["Body HTML", page.body_html],
	];
	const filled = sections.filter(([, content]) => content?.trim());
	if (!filled.length) return "This page has no data script, client script or custom HTML.";
	return filled.map(([title, content]) => `# ${title}\n\n${content!.trim()}`).join("\n\n\n");
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
			disabled: Boolean(live),
			run: async () => {
				await usePageStore().publishPage();
				toast.success("Published");
			},
		};
	},
	details() {
		const current = page.value;
		if (!current) return [];
		const path = `/${(current.route || "").replace(/^\//, "")}`;
		return [
			{ label: "Address", value: path, href: current.published ? path : undefined },
			{ label: "Sign-in", value: current.authenticated_access ? "Required" : "Not required" },
			{ label: "Indexing", value: current.disable_indexing ? "Off" : "On" },
			{ label: "Homepage", value: usePageStore().isHomePage() ? "Yes" : "No" },
			{ label: "Description", value: current.meta_description || "None" },
			{ label: "Social image", value: current.meta_image || "None", href: current.meta_image || undefined },
		];
	},
	code() {
		return { language: "text", content: page.value ? codeContent(page.value) : "" };
	},
	async reload(modified) {
		const pageStore = usePageStore();
		if (!pageStore.selectedPage) return;
		if (pageStore.savingPage) await pageStore.waitTillPageIsSaved();
		// the save this tab made itself
		if (modified && modified === pageStore.activePage?.modified) return;
		await pageStore.setPage(pageStore.selectedPage);
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
