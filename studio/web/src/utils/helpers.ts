import Block from "@web/block";
import { __ } from "@web/translation";
import getBlockTemplate from "@web/utils/blockTemplate";
import { FileUploadHandler, toast } from "frappe-ui";
import { reactive, toRaw } from "vue";
import { getRGB, HexToHSV, HSVToHex } from "./colors";
import {
	addPxToNumber,
	extractNumberAndUnit,
	getNumberFromPx,
	getSpacing,
	normalizeValueWithUnits,
	removeDefaultUnit,
	setSpacing,
	shortenNumber,
} from "./cssUtils";

function getTextContent(html: string | null) {
	if (!html || !isHTMLString(html)) {
		return html || "";
	}
	const tmp = document.createElement("div");
	tmp.innerHTML = html || "";
	const textContent = tmp.textContent || tmp.innerText || "";
	tmp.remove();
	return textContent;
}

function isHTMLString(str: string) {
	return /<[a-z][\s\S]*>/i.test(str);
}

// converts border-color to borderColor
function kebabToCamelCase(str: string) {
	return str.replace(/-([a-z])/g, function (g) {
		return g[1].toUpperCase();
	});
}

// splits an optional state prefix (hover:color) from the property name
function splitStylePrefix(style: string) {
	const separatorIndex = style.indexOf(":");
	if (separatorIndex === -1) return { prefix: "", property: style };
	return { prefix: style.slice(0, separatorIndex + 1), property: style.slice(separatorIndex + 1) };
}

// hover:border-color -> hover:borderColor
function toStyleProperty(cssProperty: string) {
	const { prefix, property } = splitStylePrefix(cssProperty);
	return `${prefix}${kebabToCamelCase(property)}` as styleProperty;
}

function getDataForKey(datum: Object, key: string) {
	const data = Object.assign({}, datum);
	const value = key
		.split(".")
		.reduce(
			(d: Record<string, any> | null, key) => (d && typeof d === "object" ? d[key] : null),
			data as Record<string, any>,
		);
	return value;
}

function getBlockInstance(options: BlockOptions | string, retainId = true): Block {
	if (typeof options === "string") {
		options = JSON.parse(options) as BlockOptions;
	}
	if (!retainId) {
		const deleteBlockId = (block: BlockOptions) => {
			delete block.blockId;
			for (let child of block.children || []) {
				deleteBlockId(child);
			}
		};
		deleteBlockId(options);
	}
	return reactive(new Block(options));
}

function getCopyWithoutParent(block: BlockOptions | Block): BlockOptions {
	const blockCopy = { ...toRaw(block) };
	blockCopy.children = blockCopy.children?.map((child) => getCopyWithoutParent(child));
	delete blockCopy.parentBlock;
	delete blockCopy.referenceComponent;
	if (!blockCopy.extendedFromComponent) {
		delete blockCopy.componentVersion;
	}
	return removeEmptyBlockValues(blockCopy);
}

function isEmptyValue(value: unknown): boolean {
	if (value === null || value === "") {
		return true;
	}
	if (Array.isArray(value)) {
		return value.length === 0;
	}
	if (value && typeof value === "object") {
		return Object.keys(value).length === 0;
	}
	return false;
}

function removeEmptyBlockValues(block: BlockOptions): BlockOptions {
	if (block.clientScript) {
		block.clientScript = { ...block.clientScript };
		for (const key of Object.keys(block.clientScript) as Array<keyof BlockClientScript>) {
			if (isEmptyValue(block.clientScript[key])) {
				delete block.clientScript[key];
			}
		}
	}
	for (const key of Object.keys(block)) {
		if (isEmptyValue(block[key])) {
			delete block[key];
		}
	}
	return block;
}

async function uploadBuilderAsset(file: File, silent = false) {
	const uploader = new FileUploadHandler();
	let fileDoc = {
		file_url: "",
		file_name: "",
	};
	const upload = uploader.upload(file, {
		private: false,
		folder: "Home/Builder Uploads",
		upload_endpoint: "/api/method/frappe.web.api.upload_builder_asset",
	});
	await new Promise((resolve) => {
		if (silent) {
			upload.then((data: { file_name: string; file_url: string }) => {
				fileDoc.file_name = data.file_name;
				fileDoc.file_url = data.file_url;
				resolve(fileDoc);
			});
			return;
		}
		toast.promise(upload, {
			loading: __("Uploading..."),
			success: (data: { file_name: string; file_url: string }) => {
				fileDoc.file_name = data.file_name;
				fileDoc.file_url = data.file_url;
				resolve(fileDoc);
				return __("Uploaded");
			},
			error: () => __("Failed to upload"),
			duration: 500,
		});
	});

	return {
		fileURL: fileDoc.file_url,
		fileName: fileDoc.file_name,
	};
}

// Naming every data URL image.png makes the server read an SVG or a GIF as a PNG,
// which fails on upload. The MIME type in the data URL already tells us what it is.
const DATA_URL_EXTENSIONS: Record<string, string> = {
	"image/svg+xml": "svg",
	"image/jpeg": "jpg",
	"image/jpg": "jpg",
	"image/webp": "webp",
	"image/gif": "gif",
	"image/avif": "avif",
	"image/png": "png",
};

// Each image also gets its own name: an upload is staged at .temp-<filename>,
// so images sharing one name delete that file from under each other.
function dataURLFileName(dataURL: string, baseName: string) {
	const mime = dataURL.match(/^data:(.*?)(;|,)/)?.[1] || "";
	const extension = DATA_URL_EXTENSIONS[mime.toLowerCase()] || "png";
	return `${baseName.replace(/\.[a-z0-9]+$/i, "")}-${generateId()}.${extension}`;
}

function dataURLtoFile(dataurl: string, filename: string) {
	try {
		let arr = dataurl.split(",");
		let mimeMatch = arr[0].match(/:(.*?)(;|,)/);
		let mime = mimeMatch ? mimeMatch[1] : "";
		let isBase64 = arr[0].includes(";base64");

		let dataString = arr.slice(1).join(",");
		let u8arr;

		if (isBase64) {
			let bstr = atob(dataString);
			let n = bstr.length;
			u8arr = new Uint8Array(n);
			while (n--) {
				u8arr[n] = bstr.charCodeAt(n);
			}
		} else {
			let decoded = decodeURIComponent(dataString);
			let n = decoded.length;
			u8arr = new Uint8Array(n);
			while (n--) {
				u8arr[n] = decoded.charCodeAt(n);
			}
		}

		return new File([u8arr], filename, { type: mime });
	} catch (error) {
		console.error(`Failed to convert dataURL ${dataurl.substring(0, 50)}... to file.`, error);
		return null;
	}
}

function handleBase64Attribute(block: Block, attrName: string, baseName: string) {
	const attrValue = block.getAttribute(attrName) as string;
	if (attrValue?.startsWith("data:image")) {
		const file = dataURLtoFile(attrValue, dataURLFileName(attrValue, baseName));
		if (file) {
			block.setAttribute(attrName, "");
			uploadBuilderAsset(file, true).then((obj) => {
				block.setAttribute(attrName, obj.fileURL);
			});
		}
	}
}

declare global {
	interface Window {
		Module: {
			decompress: (arrayBuffer: ArrayBuffer) => Uint8Array;
			onRuntimeInitialized?: () => void;
		};
	}
}

function generateId() {
	return Math.random().toString(36).slice(2, 11);
}

function getRootBlockTemplate() {
	return getBlockInstance(getBlockTemplate("body"));
}

// quote the URL so that file names with spaces or special characters stay valid CSS
const cssUrl = (url: string) => `url("${url.replace(/"/g, '\\"')}")`;

type BlockPropsWithTraceback = Record<string, BlockProps[string] & { block?: Block }>;

const getParentProps = (
	baseBlock: Block,
	baseProps: BlockPropsWithTraceback = {},
): BlockPropsWithTraceback => {
	const parentBlock = baseBlock.getParentBlock();
	if (parentBlock) {
		const parentProps: BlockPropsWithTraceback = {};
		Object.entries(parentBlock.getBlockProps())
			.filter(([_, propDetails]) => {
				return propDetails.isPassedDown;
			})
			.forEach(([propName, propDetails]) => {
				parentProps[propName] = {
					...propDetails,
					block: parentBlock,
				};
			});
		const combinedProps = { ...parentProps, ...baseProps };
		return getParentProps(parentBlock, combinedProps);
	} else {
		return baseProps;
	}
};

const PARSEABLE_STANDARD_TYPES = ["number", "boolean", "object", "array"];

// TODO: re-visit all props related functions as block props are now replaced with component props
const getPropValue = (
	propName: string,
	block: Block,
	getDataScriptValue: (path: string) => any = () => undefined,
	defaultProps?: BlockProps | null,
	getComponentScopedDataValue: (path: string) => any = () => undefined,
): any => {
	// Check default props first
	if (defaultProps?.[propName] !== undefined) {
		return defaultProps[propName].value;
	}

	let parentProps: BlockPropsWithTraceback | null = null;

	// Find matching prop from block or parent
	const blockProps = block.getBlockProps();
	let matchingProp: BlockPropsWithTraceback[string] =
		blockProps[propName] ?? (parentProps = getParentProps(block))[propName];

	if (!matchingProp) {
		return undefined;
	}

	// Handle dynamic props
	if (matchingProp.isDynamic) {
		if (matchingProp.comesFrom === "props" && matchingProp.value) {
			if (defaultProps?.[matchingProp.value] !== undefined) {
				return defaultProps[matchingProp.value].value;
			}
			if (parentProps === null) {
				parentProps = getParentProps(block);
			}
			const newMatchingProp = parentProps[matchingProp.value];
			if (!newMatchingProp?.block) return undefined;
			return getPropValue(
				matchingProp.value,
				newMatchingProp.block,
				getDataScriptValue,
				defaultProps,
				getComponentScopedDataValue,
			);
		}
		if (matchingProp.comesFrom === "dataScript" && matchingProp.value) {
			return getDataScriptValue(matchingProp.value);
		}
		if (matchingProp.comesFrom === "componentData" && matchingProp.value) {
			return getComponentScopedDataValue(matchingProp.value);
		}

		// Fallback to default props
		if (matchingProp.value && defaultProps?.[matchingProp.value] !== undefined) {
			return defaultProps[matchingProp.value].value;
		}

		return undefined;
	}

	// Handle standard props
	if (matchingProp.isStandard && matchingProp.propOptions) {
		const { type, options } = matchingProp.propOptions;
		const defaultValue = options?.defaultValue ?? null;

		if (PARSEABLE_STANDARD_TYPES.includes(type)) {
			if (matchingProp.value) {
				return JSON.parse(matchingProp.value);
			} else {
				if (typeof defaultValue === "string") {
					return JSON.parse(defaultValue);
				}
				return defaultValue;
			}
		}
		return matchingProp.value || defaultValue;
	}

	return matchingProp.value;
};

const getStandardPropValue = (
	propName: string,
	componentRoot: Block,
): { value: any; options: Record<string, any> } | undefined => {
	const propsOfComponentRoot = componentRoot.getBlockProps();
	if (propsOfComponentRoot) {
		for (const [name, value] of Object.entries(propsOfComponentRoot)) {
			if (propName === name && value.isStandard) {
				if (PARSEABLE_STANDARD_TYPES.includes(value.propOptions?.type || "string")) {
					const parsedValue = value.value
						? JSON.parse(value.value)
						: value.propOptions?.options?.defaultValue || null;
					return {
						value: parsedValue,
						options: value.propOptions?.options || {},
					};
				} else {
					return {
						value: value.value || value.propOptions?.options?.defaultValue || null,
						options: value.propOptions?.options || {},
					};
				}
			}
		}
		return undefined;
	} else {
		return undefined;
	}
};

const extractComponentId = (block: Block): string | null => block.extendedFromComponent || null;

export {
	addPxToNumber,
	cssUrl,
	dataURLFileName,
	dataURLtoFile,
	extractComponentId,
	extractNumberAndUnit,
	generateId,
	getBlockInstance,
	getCopyWithoutParent,
	getDataForKey,
	getNumberFromPx,
	getParentProps,
	getPropValue,
	getRGB,
	getRootBlockTemplate,
	getSpacing,
	getStandardPropValue,
	getTextContent,
	handleBase64Attribute,
	HexToHSV,
	HSVToHex,
	isHTMLString,
	kebabToCamelCase,
	normalizeValueWithUnits,
	removeDefaultUnit,
	setSpacing,
	shortenNumber,
	toStyleProperty,
	uploadBuilderAsset,
};
