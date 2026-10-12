// Scopes every rule a layer ships to `[data-layer="<layer>"]`, which the shell keeps on
// <html> for the layer the route is in. Each layer was its own SPA, so its global rules
// (resets, canvas selectors, its own Tailwind run) assumed the page was theirs alone.
// The attribute sits on <html> rather than a wrapper so portaled dialogs stay in scope.

import path from "node:path"

export const LAYERS = ["builder", "insights", "studio", "flow"]

const frontendDir = path.resolve(import.meta.dirname, "..")

export function layerOf(file = "") {
	const relative = path.relative(frontendDir, file.split("?")[0])
	const [first] = relative.split(path.sep)
	return LAYERS.includes(first) ? first : null
}

// selectors that start on <html> itself: the element, or the theme the color scheme stamps on it
const ON_HTML = /^(:root|html)\b/
const THEME_ON_HTML = /^(\[data-theme[^\]]*\]|\.dark\b)/

function scope(selector, attr) {
	if (selector.includes(attr)) return selector
	if (ON_HTML.test(selector)) return selector.replace(ON_HTML, `$1${attr}`)
	if (THEME_ON_HTML.test(selector)) return `${attr}${selector}`
	return `${attr} ${selector}`
}

function insideKeyframes(rule) {
	return rule.parent?.type === "atrule" && /keyframes$/i.test(rule.parent.name)
}

// a nested rule is scoped through the rule it sits in
function nested(rule) {
	for (let parent = rule.parent; parent; parent = parent.parent) {
		if (parent.type === "rule") return true
	}
	return false
}

export default function layerScope() {
	return {
		postcssPlugin: "layer-scope",
		Once(root, { result }) {
			const layer = layerOf(result.opts.from)
			if (!layer) return
			const attr = `[data-layer="${layer}"]`
			root.walkRules((rule) => {
				if (insideKeyframes(rule) || nested(rule)) return
				rule.selectors = rule.selectors.map((selector) => scope(selector, attr))
			})
		},
	}
}
layerScope.postcss = true
