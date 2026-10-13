import useCanvasStore from "@web/stores/canvasStore";
import useComponentStore from "@web/stores/componentStore";
import { findBlockInTree } from "@web/utils/block/tree";
import type { SpacingType } from "@web/utils/cssUtils";
import { cssUrl, dataURLFileName, dataURLtoFile, generateId, getBlockInstance, getSpacing, getTextContent, handleBase64Attribute, isHTMLString, kebabToCamelCase, setSpacing, toStyleProperty, uploadBuilderAsset } from "@web/utils/helpers";
import { computed, reactive } from "vue";

const TEXT_ELEMENTS = new Set([
	"span",
	"h1",
	"p",
	"b",
	"h2",
	"h3",
	"h4",
	"h5",
	"h6",
	"label",
	"a",
	"cite",
	"li",
	"strong",
	"em",
	"i",
	"blockquote",
	"summary",
]);

const HEADER_ELEMENTS = new Set(["h1", "h2", "h3", "h4", "h5", "h6"]);

// rawStyles were dropped in favour of baseStyles; older blocks still carry them
const mergeLegacyRawStyles = (baseStyles: BlockStyleMap, rawStyles?: BlockStyleMap) => {
	if (!rawStyles) return baseStyles;
	Object.entries(rawStyles).forEach(([style, value]) => {
		if (value === null || value === "" || value === undefined) return;
		baseStyles[toStyleProperty(style)] = value;
	});
	return baseStyles;
};

class Block implements BlockOptions {
	blockId: string;
	children: Array<Block>;
	baseStyles: BlockStyleMap;
	mobileStyles: BlockStyleMap;
	tabletStyles: BlockStyleMap;
	attributes: BlockAttributeMap;
	classes: Array<string>;
	dataKey?: BlockDataKey | null = null;
	blockName?: string;
	element?: string;
	draggable?: boolean;
	innerText?: string;
	innerHTML?: string;
	extendedFromComponent?: string;
	componentVersion?: string;
	originalElement?: string | undefined;
	isChildOfComponent?: string;
	referenceBlockId?: string;
	isRepeaterBlock?: boolean;
	visibilityCondition?: BlockVisibilityCondition;
	elementBeforeConversion?: string;
	parentBlock: Block | null;
	dynamicValues: Array<BlockDataKey>;
	props?: BlockProps;
	editorConfig?: BlockEditorConfig;
	clientScript: BlockClientScript;
	referenceComponent: Block | null;
	customAttributes: BlockAttributeMap;
	// a form or chat block's config; the server renders both
	form?: Record<string, unknown>;
	chat?: Record<string, unknown>;
	constructor(options: BlockOptions) {
		const componentStore = useComponentStore();
		this.element = options.element;
		this.innerHTML = options.innerHTML;
		this.extendedFromComponent = options.extendedFromComponent;
		this.componentVersion = options.componentVersion;
		this.isRepeaterBlock = options.isRepeaterBlock;
		this.isChildOfComponent = options.isChildOfComponent;
		this.referenceBlockId = options.referenceBlockId;
		this.parentBlock = options.parentBlock || null;
		if (this.extendedFromComponent) {
			if (this.componentVersion) {
				// restored/pinned instance: load the frozen version from its snapshot
				componentStore.loadComponentVersion(this.componentVersion, this.extendedFromComponent);
			} else {
				componentStore.loadComponent(this.extendedFromComponent);
			}
		} else if (this.isChildOfComponent && this.componentVersion) {
			// a pinned instance's child resolves its component from the frozen version too
			componentStore.loadComponentVersion(this.componentVersion, this.isChildOfComponent);
		}
		if (this.isChildOfComponent && !this.componentVersion) {
			let parentBlock = this.getParentBlock();
			while (parentBlock && parentBlock?.extendedFromComponent != this.isChildOfComponent) {
				parentBlock = parentBlock?.getParentBlock();
			}
			this.componentVersion = parentBlock?.componentVersion;
		}
		// to keep this property out of block reactivity
		Object.defineProperty(this, "referenceComponent", {
			value: computed(() => {
				if (this.extendedFromComponent) {
					if (this.componentVersion) {
						// prefer the pinned version; fall back to live if it was pruned
						return (
							componentStore.getComponentVersionBlock(this.componentVersion as string) ||
							componentStore.getComponentBlock(this.extendedFromComponent as string) ||
							null
						);
					}
					return componentStore.getComponentBlock(this.extendedFromComponent as string) || null;
				} else if (this.isChildOfComponent) {
					// honor the pinned version (set on restored instance children) before
					// falling back to the live component
					const componentBlock = this.componentVersion
						? componentStore.getComponentVersionBlock(this.componentVersion as string) ||
						  componentStore.getComponentBlock(this.isChildOfComponent as string)
						: componentStore.getComponentBlock(this.isChildOfComponent as string);
					return findBlockInTree(this.referenceBlockId as string, [componentBlock]);
				}
				return null;
			}),
			enumerable: false,
		});

		this.dataKey = options.dataKey || null;

		if (options.innerText) {
			this.innerHTML = options.innerText;
		}

		if (typeof options.visibilityCondition == "string") {
			this.visibilityCondition = {
				key: options.visibilityCondition,
				comesFrom: "dataScript",
			};
		} else {
			this.visibilityCondition = options.visibilityCondition;
		}

		this.originalElement = options.originalElement;

		if (!options.blockId || options.blockId === "root") {
			this.blockId = generateId();
		} else {
			this.blockId = options.blockId;
		}
		this.children = (options.children || []).map((child: BlockOptions) => {
			child.parentBlock = this;
			return getBlockInstance(child);
		});

		this.baseStyles = reactive(
			mergeLegacyRawStyles({ ...(options.styles || options.baseStyles || {}) }, options.rawStyles),
		);
		this.customAttributes = reactive(options.customAttributes || {});
		this.mobileStyles = reactive(options.mobileStyles || {});
		this.tabletStyles = reactive(options.tabletStyles || {});
		this.attributes = reactive(options.attributes || {});
		this.dynamicValues = reactive(options.dynamicValues || []);
		this.props = reactive(options.props || {});
		this.editorConfig = options.editorConfig;
		this.clientScript = reactive(
			options.clientScript ?? (options.blockClientScript ? { js: options.blockClientScript } : {}),
		);

		this.blockName = options.blockName;
		this.form = options.form;
		this.chat = options.chat;
		delete this.attributes.style;
		this.classes = options.classes || [];

		if (this.isRoot()) {
			this.blockId = "root";
			this.draggable = false;
			this.removeStyle("minHeight");
		}

		if (this.isImage()) {
			handleBase64Attribute(this, "src", "image");
			handleBase64Attribute(this, "darkSrc", "image-dark");
		}

		const bgImage = this.getStyle("backgroundImage") as string;
		if (bgImage && /^url\(['"]?data:image/.test(bgImage)) {
			let bgImage = this.getStyle("backgroundImage") as string;
			const dataURL = bgImage.match(/url\(['"]?(.*?)['"]?\)/)?.[1];

			const file = dataURLtoFile(dataURL as string, dataURLFileName(dataURL as string, "background"));

			if (file) {
				this.setStyle("backgroundImage", "");
				uploadBuilderAsset(file, true).then((obj) => {
					this.setStyle("backgroundImage", cssUrl(obj.fileURL));
				});
			}
		}
	}
	getStyles(breakpoint: string = "desktop"): BlockStyleMap {
		let styleObj = {};
		if (this.isExtendedFromComponent()) {
			styleObj = this.getComponentStyles(breakpoint);
		}
		styleObj = { ...styleObj, ...this.baseStyles };
		if (["mobile", "tablet"].includes(breakpoint)) {
			styleObj = { ...styleObj, ...this.tabletStyles };
			if (breakpoint === "mobile") {
				styleObj = { ...styleObj, ...this.mobileStyles };
			}
		}
		// replace variables with values
		// Object.keys(styleObj).forEach((style) => {
		// 	const value = styleObj[style];
		// 	if (typeof value === "string" && value.startsWith("--")) {
		// 		styleObj[style] = this.getVariableValue(value);
		// 	}
		// });

		return styleObj;
	}
	resetOverrides(breakpoint: string) {
		if (breakpoint === "mobile") {
			this.mobileStyles = {};
		}
		if (breakpoint === "tablet") {
			this.tabletStyles = {};
		}
	}
	getComponentStyles(breakpoint: string): BlockStyleMap {
		return this.referenceComponent?.getStyles(breakpoint) || {};
	}
	getAttributes(): BlockAttributeMap {
		let attributes = {};
		if (this.isExtendedFromComponent()) {
			attributes = this.getComponentAttributes();
		}
		attributes = { ...attributes, ...this.attributes };
		return attributes;
	}
	getComponentAttributes() {
		return this.referenceComponent?.attributes || {};
	}
	getClasses() {
		let classes = [] as Array<string>;
		if (this.isExtendedFromComponent()) {
			classes = this.getComponentClasses();
		}
		classes = [...classes, ...this.classes];
		return classes;
	}
	getComponentClasses() {
		return this.referenceComponent?.classes || [];
	}
	getChildren() {
		return this.children;
	}
	hasChildren() {
		return this.getChildren().length > 0;
	}
	getCustomAttributes(): BlockAttributeMap {
		let customAttributes = {};
		if (this.isExtendedFromComponent()) {
			customAttributes = this.referenceComponent?.customAttributes || {};
		}
		customAttributes = { ...customAttributes, ...this.customAttributes };
		return customAttributes;
	}
	getVisibilityCondition() {
		let visibilityCondition = this.visibilityCondition;
		if (this.isExtendedFromComponent() && this.referenceComponent?.visibilityCondition) {
			visibilityCondition = this.referenceComponent?.visibilityCondition;
		}
		return visibilityCondition;
	}
	getTextContent() {
		return getTextContent(this.getInnerHTML() || "");
	}
	isImage() {
		return this.getElement() === "img";
	}
	isButton() {
		return this.getElement() === "button";
	}
	isLink() {
		return this.getElement() === "a";
	}
	isSVG() {
		return this.getElement() === "svg" || this.getInnerHTML()?.startsWith("<svg");
	}
	isInlineSVG() {
		return this.isSVG() && Boolean(this.getInnerHTML());
	}
	isText() {
		if (TEXT_ELEMENTS.has(this.getElement() as string)) return true;
		// an option holds only a text node, which BuilderBlock writes itself
		if (this.getElement() === "option") return false;
		// the published page renders any element's text, so a div that carries text is a text block too
		const innerHTML = this.getInnerHTML();
		if (innerHTML) return !isHTMLString(innerHTML);
		return !this.isRepeater() && this.getDynamicValues().some((value) => value.property === "innerHTML");
	}
	isHeader() {
		return HEADER_ELEMENTS.has(this.getElement() as string);
	}
	isInput() {
		return (
			this.originalElement === "input" || this.getElement() === "input" || this.getElement() === "textarea"
		);
	}
	setStyle(style: styleProperty, value: StyleValue) {
		const canvasStore = useCanvasStore();
		let styleObj = this.baseStyles;
		style = kebabToCamelCase(style as string) as styleProperty;
		if (canvasStore.activeCanvas?.activeBreakpoint === "mobile") {
			styleObj = this.mobileStyles;
		} else if (canvasStore.activeCanvas?.activeBreakpoint === "tablet") {
			styleObj = this.tabletStyles;
		}
		if (value === null || value === "") {
			delete styleObj[style];
			return;
		}
		styleObj[style] = value;
	}
	setAttribute(attribute: string, value: string | undefined) {
		this.attributes[attribute] = value;
	}
	removeAttribute(attribute: string) {
		this.setAttribute(attribute, undefined);
	}
	getAttribute(attribute: string) {
		return this.getAttributes()[attribute];
	}
	removeStyle(style: styleProperty) {
		delete this.baseStyles[style];
		delete this.mobileStyles[style];
		delete this.tabletStyles[style];
	}
	getStyle(
		style: styleProperty,
		breakpoint?: string | null,
		nativeOnly: boolean = false,
		cascading: boolean = false,
	): StyleValue | undefined {
		const canvasStore = useCanvasStore();
		const currentBreakpoint = breakpoint || canvasStore.activeCanvas?.activeBreakpoint || "desktop";

		if (nativeOnly) {
			const styleMap = this.getStyleMapForBreakpoint(currentBreakpoint);
			return styleMap[style];
		}

		if (cascading) {
			return this.getStyleWithCascading(style, currentBreakpoint);
		}

		const styleValue = this.getInheritedStyleValue(style, currentBreakpoint);

		return styleValue ?? this.getComponentStyleFallback(style, currentBreakpoint, nativeOnly, cascading);
	}

	private getStyleMapForBreakpoint(breakpoint: string) {
		const styleMap = {
			mobile: this.mobileStyles,
			tablet: this.tabletStyles,
			desktop: this.baseStyles,
		};
		return styleMap[breakpoint as keyof typeof styleMap] || this.baseStyles;
	}

	private getStyleWithCascading(style: styleProperty, breakpoint: string): StyleValue | undefined {
		if (this.isExtendedFromComponent()) {
			const componentValue = this.referenceComponent?.getStyle(style, breakpoint, true, false);
			if (componentValue) return componentValue;
		}

		const fallbackBreakpoints = {
			mobile: ["tablet", "desktop"],
			tablet: ["desktop"],
		};

		const fallbacks = fallbackBreakpoints[breakpoint as keyof typeof fallbackBreakpoints] || [];
		for (const fallbackBreakpoint of fallbacks) {
			const value = this.getStyle(style, fallbackBreakpoint);
			if (value) return value;
		}

		return this.getStyle(style, "desktop");
	}

	private getInheritedStyleValue(style: styleProperty, breakpoint: string): StyleValue | undefined {
		switch (breakpoint) {
			case "mobile":
				return this.mobileStyles[style] || this.tabletStyles[style] || this.baseStyles[style];
			case "tablet":
				return this.tabletStyles[style] || this.baseStyles[style];
			default:
				return this.baseStyles[style];
		}
	}

	private getComponentStyleFallback(
		style: styleProperty,
		breakpoint: string,
		nativeOnly: boolean,
		cascading: boolean,
	): StyleValue | undefined {
		if (!this.isExtendedFromComponent()) return undefined;
		return this.referenceComponent?.getStyle?.(style, breakpoint, nativeOnly, cascading);
	}
	isRoot() {
		return this.originalElement === "body";
	}
	getTag(): string {
		if (this.isButton() || this.isLink()) {
			return "div";
		}
		return this.getElement() || "div";
	}
	isMovable(): boolean {
		return ["absolute", "fixed"].includes(this.getStyle("position") as string);
	}
	getEditorStyles() {
		const styles = reactive({} as BlockStyleMap);

		if (this.isRoot()) {
			styles.width = "inherit";
			styles.overflowX = "hidden";
		}

		if (this.isImage() && !this.getAttribute("src")) {
			styles.background = `repeating-linear-gradient(45deg, rgba(180, 180, 180, 0.8) 0px, rgba(180, 180, 180, 0.8) 1px, rgba(255, 255, 255, 0.2) 0px, rgba(255, 255, 255, 0.2) 50%)`;
			styles.backgroundSize = "16px 16px";
		}

		if (this.isButton() && this.children.length === 0 && this.isVisible()) {
			styles.display = "flex";
			styles.alignItems = "center";
			styles.justifyContent = "center";
		}
		styles.transition = "unset";

		return styles;
	}
	getParentBlock(): Block | null {
		return this.parentBlock || null;
	}
	getAncestorStyle(style: styleProperty, breakpoint?: string): StyleValue | undefined {
		let parent = this.getParentBlock();
		while (parent) {
			const value = parent.getStyle(style, breakpoint);
			if (value) return value;
			parent = parent.getParentBlock();
		}
	}
	isHTML() {
		return this.originalElement === "__raw_html__" || (isHTMLString(this.getInnerHTML()) && !this.isText());
	}
	isExtendedFromComponent() {
		return Boolean(this.extendedFromComponent) || Boolean(this.isChildOfComponent);
	}
	getComponentRoot(): Block | null {
		let block: Block | null = this;
		if (!block.isExtendedFromComponent()) return null;

		while (block && block.isExtendedFromComponent()) {
			if (block.extendedFromComponent) return block;
			block = block.getParentBlock()!;
		}
		return block;
	}
	getPropsRoot(): Block | null {
		const componentRoot = this.getComponentRoot();
		if (componentRoot) return componentRoot;

		let block: Block | null = this;
		while (block) {
			if (Object.keys(block.props || {}).length > 0) return block;
			block = block.getParentBlock();
		}
		return null;
	}
	isRepeater() {
		return Boolean(this.isRepeaterBlock);
	}
	getDataKey(key: keyof BlockDataKey): string {
		let dataKey = (this.dataKey && this.dataKey[key]) || "";
		if (!dataKey && this.isExtendedFromComponent()) {
			dataKey = this.referenceComponent?.getDataKey(key) || "";
		}
		return dataKey;
	}
	getInnerHTML(): string {
		let innerHTML = this.innerHTML || "";
		if (!innerHTML && this.isExtendedFromComponent()) {
			innerHTML = this.referenceComponent?.getInnerHTML() || "";
		}
		return String(innerHTML);
	}
	setInnerHTML(innerHTML: string) {
		this.innerHTML = innerHTML;
	}
	isVisible(breakpoint?: string) {
		return this.getStyle("display", breakpoint) !== "none";
	}
	convertToLink() {
		this.elementBeforeConversion = this.element;
		this.element = "a";
	}
	unsetLink() {
		this.removeAttribute("href");
		this.removeAttribute("target");
		if (this.elementBeforeConversion) {
			this.element = this.elementBeforeConversion;
		}
	}
	getElement() {
		if (!this.element && this.isExtendedFromComponent()) {
			return this.referenceComponent?.element;
		}
		return this.element;
	}
	setSpacing(type: SpacingType, value: string) {
		setSpacing(this, type, value);
	}
	getSpacing(type: SpacingType, opts?: { nativeOnly?: boolean; cascading?: boolean }) {
		return getSpacing(this, type, opts);
	}
	getDynamicValues() {
		const dynamicValues = [...this.dynamicValues];
		const dynamicValueProperties = dynamicValues.map((v) => v.property);
		if (this.isExtendedFromComponent()) {
			const componentDynamicValues = this.referenceComponent?.getDynamicValues() || [];
			componentDynamicValues.forEach((v) => {
				if (!dynamicValueProperties.includes(v.property)) {
					dynamicValues.push(v);
				}
			});
		}
		return dynamicValues;
	}
	getBlockProps(): BlockProps {
		const propsRoot = this.getPropsRoot();
		if (!propsRoot) return { ...(this.props || {}) };
		const referenceProps = propsRoot.extendedFromComponent ? propsRoot.referenceComponent?.props || {} : {};
		return { ...referenceProps, ...(propsRoot.props || {}) };
	}
}

export default Block;
