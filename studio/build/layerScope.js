// Scopes every rule a layer ships to the part of the page that layer owns. Each layer was
// its own SPA, so its global rules (resets, canvas selectors, its own Tailwind run) assumed
// the page was theirs alone. The shell marks ownership with data-layer: on <html> for the
// layer the route is in, so portaled dialogs stay in scope, and on any element that hosts
// another layer inside it, such as the chat beside an editor. `@scope ... to ...` stops a
// layer's rules at the nearest element owned by another layer.

import path from "node:path"

export const LAYERS = ["web", "analytics", "ui", "ai"]

const frontendDir = path.resolve(import.meta.dirname, "..")

export function layerOf(file = "") {
	const relative = path.relative(frontendDir, file.split("?")[0])
	const [first] = relative.split(path.sep)
	return LAYERS.includes(first) ? first : null
}

// @scope may hold style rules and the conditional groups around them, nothing else
const SCOPABLE_AT_RULES = new Set(["media", "supports", "container"])
const scopable = (node) => node.type === "rule" || (node.type === "atrule" && SCOPABLE_AT_RULES.has(node.name))

// a rule written for the page itself now means the layer's own root
const ON_PAGE_ROOT = /^(:root|html)\b/
const onScopeRoot = (selector) => selector.replace(ON_PAGE_ROOT, ":scope")

export default function layerScope() {
	return {
		postcssPlugin: "layer-scope",
		Once(root, { result, AtRule }) {
			const layer = layerOf(result.opts.from)
			if (!layer) return
			const owner = `[data-layer="${layer}"]`
			const scope = new AtRule({ name: "scope", params: `(${owner}) to ([data-layer]:not(${owner}))` })
			for (const node of root.nodes.filter(scopable)) scope.append(node.remove())
			scope.walkRules((rule) => {
				rule.selectors = rule.selectors.map(onScopeRoot)
			})
			if (scope.nodes.length) root.append(scope)
		},
	}
}
layerScope.postcss = true
