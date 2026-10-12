declare global {
	interface Window {
		insights_path?: string
	}
}

/**
 * The path this site serves the Insights app from (site config `insights_path`).
 *
 * The server sends it in two places. The app's www page puts it in the page
 * boot. `extend_bootinfo` in `frappe.insights.desk` puts it in desk's boot, and a desk
 * island reads it from there. The island builds its links from this path.
 * Without it, a site that serves the app elsewhere gives the island's links a
 * 404.
 *
 * The app is one layer of the framework's SPA, whose router has no base, so the
 * layer is mounted at this path and every route of it starts with it.
 */
export const APP_PATH =
	window.insights_path || (window as any).frappe?.boot?.insights_path || '/insights'

/** An Insights route as the full path the router matches: `appPath('/workbook')`. */
export function appPath(path: string = '') {
	return `${APP_PATH}${path}`
}
