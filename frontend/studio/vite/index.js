import fs from "node:fs"
import path from "node:path"

import sharedDependencyResolver from "./sharedDependencyResolver.js"
import studioFolderWatcher from "./studioFolderWatcher.js"
import studioRootAlias from "./studioRootAlias.js"

// What the frontend dev server needs to serve the bench apps' exported studio apps (custom
// components, page scripts, router.ts under <app>/studio/) to the editor and the renderer
export default function studio({ frontendDir, appsDir }) {
	return [
		studioRootAlias(),
		sharedDependencyResolver(frontendDir),
		studioFolderWatcher(appsDir),
		{
			name: "studio-app-folders",
			apply: "serve",
			config: () => ({ server: { fs: { allow: [appsDir, ...symlinkedStudioFolders(appsDir)] } } }),
		},
	]
}

// Apps can be symlinked into apps/ from elsewhere (e.g. git worktrees); allow only their studio/ folder
function symlinkedStudioFolders(appsDir) {
	return fs.readdirSync(appsDir).flatMap((entry) => {
		try {
			const realPath = fs.realpathSync(path.join(appsDir, entry))
			if (realPath.startsWith(appsDir + path.sep)) return []
			const studioDir = path.join(realPath, "studio")
			return fs.existsSync(studioDir) ? [studioDir] : []
		} catch {
			return []
		}
	})
}
