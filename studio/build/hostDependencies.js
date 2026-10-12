// Source packages linked from elsewhere in the repo (@flow/ui-core) are compiled in place,
// so their bare imports would resolve by walking up from their own folder, into the desk's
// node_modules or nowhere. Resolve them as if this app imported them, so every package
// has one copy.

import path from "node:path"

export default function hostDependencies(roots) {
	let hostImporter
	return {
		name: "host-dependencies",
		enforce: "pre",
		configResolved(config) {
			hostImporter = path.join(config.root, "index.html")
		},
		resolveId(source, importer, options) {
			if (!importer || !roots.some((root) => importer.startsWith(root))) return null
			if (/^[./\0]/.test(source) || path.isAbsolute(source)) return null
			return this.resolve(source, hostImporter, { ...options, skipSelf: true })
		},
	}
}
