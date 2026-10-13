// Builder Page in Studio's editor shell: the page as the preview, and the shell's contract
// answered from the page store.
import type Block from "@web/block";
import BuilderCanvas from "@web/components/BuilderCanvas.vue";
import CodeView from "@web/components/CodeView.vue";
import PageDetails from "@web/components/PageDetails.vue";
import { webPages } from "@web/data/webPage";
import useCanvasStore from "@web/stores/canvasStore";
import usePageStore from "@web/stores/pageStore";
import type { BuilderPage } from "@web/types/doctypes";
import { getBlockInstance, getCopyWithoutParent, getRootBlockTemplate } from "@web/utils/helpers";
import { useDebounceFn } from "@vueuse/core";
import { type CodeTab, type ElementAction, type ElementProperty, defineArtifactEditor } from "@shell/editor";
import { LoadingIndicator, toast } from "frappe-ui";
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
			// the page as a sheet on the canvas, so its own backgrounds read as the page's
			h("div", { ref: root, class: "relative h-full bg-surface-gray-1 p-6" }, [
				h("div", { class: "h-full overflow-hidden rounded-4 border border-outline-gray-1 bg-white" }, [
					pageStore.pageBlocks[0]
						? h(BuilderCanvas, {
								ref: canvas,
								blockData: pageStore.pageBlocks[0],
								class: ["transition-opacity duration-150", pageStore.settingPage ? "opacity-0" : "opacity-100"],
							})
						: null,
				]),
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

function parentOf(id: string, block = useCanvasStore().activeCanvas?.getRootBlock() as Block | undefined): Block | null {
	for (const child of block?.children ?? []) {
		if (child.blockId === id) return block!;
		const parent = parentOf(id, child);
		if (parent) return parent;
	}
	return null;
}

function duplicate(block: Block, parent: Block) {
	const copy = JSON.parse(JSON.stringify(getCopyWithoutParent(block)));
	copy.parentBlock = parent;
	const added = getBlockInstance(copy, false);
	parent.children.splice(parent.children.indexOf(block) + 1, 0, added);
	save();
	return added.blockId;
}

function remove(block: Block, parent: Block) {
	parent.children.splice(parent.children.indexOf(block), 1);
	save();
}

function kind(block: Block) {
	if (block.isRoot()) return { label: "Page", icon: "lucide-file" };
	if (block.form) return { label: "Form", icon: "lucide-text-cursor-input" };
	if (block.chat) return { label: "Chat", icon: "lucide-message-circle" };
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
const DEFAULT_NAMES = new Set(["body", "container", "text", "image", "button", "button-link", "link", "html", "repeater", "section"]);
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

function linkProperty(block: Block): ElementProperty {
	return {
		name: "link",
		label: "Link",
		icon: "lucide-link",
		type: "text",
		placeholder: "/schedule or https://",
		value: String(block.getAttribute("href") ?? ""),
		set(href) {
			if (!href) block.isLink() && block.unsetLink();
			else {
				if (!block.isLink()) block.convertToLink();
				block.setAttribute("href", href);
			}
			save();
		},
	};
}

function imageProperty(block: Block): ElementProperty {
	return {
		name: "image",
		label: "Replace image",
		icon: "lucide-image-up",
		type: "upload",
		accept: "image/*",
		value: String(block.getAttribute("src") ?? ""),
		set(src) {
			block.setAttribute("src", src);
			save();
		},
	};
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
		// a form or a chat is not a link
		...(block.form || block.chat ? [] : [linkProperty(block)]),
		...(block.isImage() ? [imageProperty(block)] : []),
		...(hasText(block) ? [alignProperty(block)] : []),
		visibilityProperty(block),
	];
}

// the HTML and CSS tabs share one render of the page per version
let pageCode: { key: string; code: Promise<{ html: string; css: string }> } | null = null;
function loadPageCode(page: BuilderPage) {
	const key = `${page.name}:${page.modified}`;
	if (pageCode?.key !== key) {
		const code = webPages.runDocMethod
			.submit({ method: "get_code", name: page.name, route_variables: usePageStore().routeVariables })
			.then((response: { message: { html: string; css: string } }) => response.message);
		pageCode = { key, code };
	}
	return pageCode.code;
}

function codeTabs(page: BuilderPage): CodeTab[] {
	const pageStore = usePageStore();
	const tab = (name: string, label: string, code: string | null | undefined, language: string): CodeTab[] =>
		code?.trim() ? [{ name, label, component: { component: CodeView, props: { code: code.trim(), language } } }] : [];
	const rendered = (name: "html" | "css", label: string): CodeTab => ({
		name,
		label,
		component: {
			component: CodeView,
			props: { load: () => loadPageCode(page).then((code) => code[name]), version: page.modified, language: name },
		},
	});
	return [
		rendered("html", "HTML"),
		rendered("css", "CSS"),
		...tab("data_script", "Data script", page.page_data_script, "python"),
		...tab("data", "Data", page.page_data_script ? JSON.stringify(pageStore.pageData, null, 2) : null, "javascript"),
		...pageStore.activePageScripts.flatMap((script) =>
			tab(script.name, script.name, script.script, script.script_type === "CSS" ? "css" : "javascript"),
		),
		...tab("head_html", "Head HTML", page.head_html, "html"),
		...tab("body_html", "Body HTML", page.body_html, "html"),
	];
}

const page = computed(() => usePageStore().activePage);

export default defineArtifactEditor({
	preview: BuilderPagePreview,

	title() {
		// blank until the page the route names has loaded, not the last page's title
		if (!page.value || page.value.name !== usePageStore().selectedPage) return "";
		return page.value.page_title || "Untitled page";
	},
	rename: (title) => usePageStore().updateActivePage("page_title", title) as Promise<unknown>,
	status() {
		if (usePageStore().savingPage) return { label: "Saving…", theme: "gray" };
		if (!page.value?.published) return { label: "Draft", theme: "gray" };
		if (page.value.draft_blocks) return { label: "Unpublished changes", theme: "orange" };
		return { label: "Published", theme: "green" };
	},
	primaryAction() {
		const current = page.value;
		// a live page's status already says so; the action opens it
		if (current?.published && !current.draft_blocks)
			return {
				label: "Open",
				icon: "lucide-external-link",
				run: async () => void window.open(`/${(current.route || "").replace(/^\//, "")}`, "_blank"),
			};
		return {
			label: "Publish",
			run: async () => {
				await usePageStore().publishPage();
				toast.success("Published");
			},
		};
	},
	modes: ["edit", "preview"],
	detailsForm: () => (page.value ? { component: PageDetails } : null),
	details() {
		const current = page.value;
		if (!current) return [];
		const path = `/${(current.route || "").replace(/^\//, "")}`;
		return [
			...(current.published ? [{ label: "Live page", value: path, href: path }] : []),
			{ label: "Homepage", value: usePageStore().isHomePage() ? "Yes" : "No" },
		];
	},
	code: () => ({ language: "text", content: "" }),
	codeTabs: () => (page.value ? codeTabs(page.value) : []),
	async reload(modified) {
		const pageStore = usePageStore();
		if (!pageStore.selectedPage) return;
		if (pageStore.savingPage) await pageStore.waitTillPageIsSaved();
		// the save this tab made itself
		if (modified && modified === pageStore.activePage?.modified) return;
		await pageStore.setPage(pageStore.selectedPage);
	},
	undo: () => usePageStore().undo(),
	redo: () => usePageStore().redo(),

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
	actions(id): ElementAction[] {
		const block = findBlock(id);
		const parent = parentOf(id);
		if (!block || !parent) return [];
		return [
			{ name: "duplicate", label: "Duplicate", icon: "lucide-copy", run: () => duplicate(block, parent) },
			{ name: "delete", label: "Delete", icon: "lucide-trash-2", run: () => remove(block, parent) },
		];
	},
});
