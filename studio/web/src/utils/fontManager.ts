import userFont from "@web/data/userFonts";
import { useBuilderToken } from "@web/utils/useBuilderToken";
import { shallowRef } from "vue";

interface FontListItem {
	family: string;
	variants: string[];
}

const GF_CSS = "https://fonts.googleapis.com/css2";
const fontCache = new Map<string, Promise<string>>();

// the Google Fonts catalog is ~110KB, so it stays out of the main bundle
// and loads on first use (font pickers read the reactive ref)
const fontListItems = shallowRef<FontListItem[]>([]);
let fontListPromise: Promise<FontListItem[]> | null = null;

export function loadFontList(): Promise<FontListItem[]> {
	if (!fontListPromise) {
		fontListPromise = import("@web/utils/fontList.json").then((m) => {
			fontListItems.value = m.default.items as FontListItem[];
			return fontListItems.value;
		});
	}
	return fontListPromise;
}

function loadCustomFont(font: string, url: string): Promise<string> {
	return new FontFace(font, `url("${url}")`)
		.load()
		.then((face) => {
			document.fonts.add(face);
			return font;
		})
		.catch(() => {
			console.warn(`Failed to load custom font: ${font}`);
			return font;
		});
}

// the catalogue names 400 "regular" / "italic" and every other weight "500" / "500italic"
function variantName(weight: string, italic: boolean): string {
	if (weight === "400") return italic ? "italic" : "regular";
	return italic ? `${weight}italic` : weight;
}

/** Does this family actually carry the weight (in italic)? The css2 API answers a
 * wght@ it doesn't have with a 400 — which the browser then reports as a CORS failure,
 * since an error response carries no allow-origin header. Asking the catalogue
 * first turns a guaranteed round trip plus retry into a lookup. */
async function carriesVariant(font: string, weight: string, italic = false): Promise<boolean> {
	const items = fontListItems.value.length ? fontListItems.value : await loadFontList().catch(() => []);
	const entry = items.find((item) => item.family === font);
	// Unknown family: let the request decide, the retry below still covers it.
	if (!entry) return true;
	return entry.variants.includes(variantName(weight, italic)) || (!italic && entry.variants.includes(weight));
}

/** A system font (Arial, Comic Sans MS) or an unregistered custom family is not on
 * Google Fonts; requesting it anyway costs a round trip that ends in a CORS error. */
async function inGoogleCatalog(font: string): Promise<boolean> {
	const items = fontListItems.value.length ? fontListItems.value : await loadFontList().catch(() => []);
	// a catalog that failed to load must not block every font
	return !items.length || items.some((item) => item.family === font);
}

async function loadGoogleFont(font: string, weight?: string, italic = false): Promise<string> {
	if (!(await inGoogleCatalog(font))) return font;
	if (weight && !(await carriesVariant(font, weight))) weight = undefined;
	// without a real italic the browser slants the roman, same as on the published page
	if (italic && !(await carriesVariant(font, weight ?? "400", true))) italic = false;
	const italicWeight = weight ?? "400";
	const axes = italic ? `ital,wght@0,${italicWeight};1,${italicWeight}` : weight ? `wght@${weight}` : "";
	return new Promise<string>((resolve) => {
		const attempt = (withAxes: boolean) => {
			const familyParam = withAxes ? `${encodeURIComponent(font)}:${axes}` : encodeURIComponent(font);
			const link = document.createElement("link");
			link.id = `gf-${font.replace(/\s+/g, "-")}${withAxes ? `-${italic ? `${italicWeight}i` : weight}` : ""}`;
			link.rel = "stylesheet";
			link.crossOrigin = "anonymous";
			link.href = `${GF_CSS}?family=${familyParam}&display=swap`;
			link.addEventListener("load", () => resolve(font), { once: true });
			link.addEventListener(
				"error",
				() => {
					link.remove();
					if (withAxes) {
						// Single-weight faces (Italiana, Young Serif, Caprasimo…) 400 on ANY
						// wght@ request — the css2 API rejects weights a family doesn't carry.
						// Retry the family default; the browser synthesises the bold.
						attempt(false);
						return;
					}
					console.warn(`Failed to load font: ${font}`);
					resolve(font);
				},
				{ once: true },
			);
			document.head.appendChild(link);
		};
		attempt(!!axes);
	});
}

// A Font design token (fontFamily: var(--id)) stands in for its family, so every
// caller can work with the family without knowing whether a style is tokenized.
function resolveFontToken(font: string): string {
	if (!font.includes("var(")) return font;
	const { resolveVariableValue } = useBuilderToken();
	const resolved = resolveVariableValue(font);
	return resolved === font ? "" : resolved; // unknown token: no family to work with
}

export function setFont(font: string | null, weight?: string, italic = false): Promise<string> {
	if (!font) return Promise.resolve("");

	// a token stands in for its family; an unknown one leaves nothing to load
	const family = font.includes("var(") ? resolveFontToken(font) : font;
	if (!family) return Promise.resolve(font);

	const cacheKey = [family, weight, italic && "italic"].filter(Boolean).join(":");
	if (fontCache.has(cacheKey)) return fontCache.get(cacheKey)!;

	// userFont list resource may not have loaded yet (e.g. a page rendered right
	// after navigation); fall back to treating it as a Google font until it does.
	const customFont = (userFont.data || []).find(
		(f: { font_name: string; font_file: string }) => f.font_name === family,
	);

	const promise = customFont
		? loadCustomFont(family, customFont.font_file)
		: loadGoogleFont(family, weight, italic);

	fontCache.set(cacheKey, promise);
	return promise;
}

const ITALIC_MARKUP = /<(em|i)\b|font-style\s*:\s*(italic|oblique)/i;

/** Does a block's text need italic faces? Mirrors what the renderer requests for the
 * published page: its own font-style, or <em>/<i>/inline font-style in its HTML. */
export function needsItalic(fontStyle: unknown, html?: string | null): boolean {
	return /italic|oblique/.test(String(fontStyle ?? "")) || ITALIC_MARKUP.test(html ?? "");
}

export function setFontFromHTML(html: string): void {
	const matches = html.match(/font-family:\s*([^;"]+)[";]/g) ?? [];
	matches
		.map((m) => m.replace(/font-family:\s*([^;"]+)[";]/, "$1").trim())
		.filter(Boolean)
		.forEach((font) => setFont(font));
}

export {
	fontListItems,
};
