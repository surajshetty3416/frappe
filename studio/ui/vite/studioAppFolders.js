import fs from "node:fs"
import path from "node:path"

// Bench apps export studio apps to <app>/studio/<studio_app>/. Frappe's own studio/ folder is the
// Studio SPA, so there only the folders frappe/ui/studio_apps.txt lists are studio apps.
export function isStudioApp(appsDir, frappeApp, folder) {
	return frappeApp !== "frappe" || frappeStudioApps(appsDir).includes(folder)
}

export function findStudioAppFolders(appsDir) {
	return fs.readdirSync(appsDir).flatMap((frappeApp) => studioAppFolders(appsDir, frappeApp))
}

function studioAppFolders(appsDir, frappeApp) {
	const studioDir = path.join(appsDir, frappeApp, "studio")
	return listFolders(studioDir)
		.filter((folder) => isStudioApp(appsDir, frappeApp, folder))
		.map((folder) => path.join(studioDir, folder))
}

// Tailwind content globs for every exported studio app. Tailwind applies a negated glob to all the
// others, so none may reach the SPA's own node_modules, where frappe-ui's sources are scanned.
export function studioAppContent(appsDir) {
	return contentFolders(appsDir).flatMap((folder) => [
		`${folder}/**/*.{vue,js,ts,jsx,tsx,json}`,
		`!${folder}/**/node_modules/**`,
	])
}

// a whole studio/ folder where it holds only studio apps, so apps exported later are scanned too
function contentFolders(appsDir) {
	return fs.readdirSync(appsDir).flatMap((frappeApp) => {
		const studioDir = path.join(appsDir, frappeApp, "studio")
		if (frappeApp === "frappe") return studioAppFolders(appsDir, frappeApp)
		return fs.existsSync(studioDir) ? [studioDir] : []
	})
}

function frappeStudioApps(appsDir) {
	const file = path.join(appsDir, "frappe", "frappe", "ui", "studio_apps.txt")
	if (!fs.existsSync(file)) return []
	return fs
		.readFileSync(file, "utf8")
		.split("\n")
		.map((line) => line.trim())
		.filter((line) => line && !line.startsWith("#"))
}

function listFolders(folder) {
	if (!fs.existsSync(folder)) return []
	return fs
		.readdirSync(folder, { withFileTypes: true })
		.filter((entry) => entry.isDirectory())
		.map((entry) => entry.name)
}
