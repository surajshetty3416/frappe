declare global {
	interface Window {
		insights_path?: string
	}
}

// unit tests import this in Node, which has no window
const page = typeof window === 'undefined' ? undefined : window

/**
 * The path Studio mounts the Insights app at (`insights_path` in `frappe/analytics/hooks.py`).
 *
 * The server sends it in two places. Studio's page puts it in the page boot.
 * `extend_bootinfo` in `frappe.analytics.desk` puts it in desk's boot, and a desk
 * island reads it from there. The island builds its links from this path.
 *
 * The app is one layer of Studio's SPA, whose router has no base, so the layer
 * is mounted at this path and every route of it starts with it.
 */
export const APP_PATH =
	page?.insights_path || page?.frappe?.boot?.insights_path || '/studio/analytics'

/** An Insights route as the full path the router matches: `appPath('/workbook')`. */
export function appPath(path: string = '') {
	return `${APP_PATH}${path}`
}
