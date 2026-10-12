// Setup shared by every Insights island entry. It lives in one module so the
// entries cannot drift apart.

import { mountVueIsland } from '@framework/ui/island'
import { frappeRequest, setConfig } from 'frappe-ui'
import { setRouter } from '../helpers/navigation'
import session from '../session'
import { configureIsland } from './configure'

declare global {
	interface Window {
		frappe?: any
		translated_messages?: Record<string, string>
	}
}

setConfig('resourceFetcher', frappeRequest)

// frappe-ui reads the CSRF token from `window`, but desk sets it on `frappe`.
// Without this, the server rejects every write the island makes.
if (!window.csrf_token && window.frappe?.csrf_token) {
	window.csrf_token = window.frappe.csrf_token
}

// The host page already holds the site's translations, so reuse them.
if (!window.translated_messages && window.frappe?._messages) {
	window.translated_messages = window.frappe._messages
}

setRouter({
	// A route in the island is an Insights page (built with `appPath`), and the
	// host page is not the SPA, so the href is absolute. Only a string route
	// resolves. A named SPA route gives an empty href, and the island shows no
	// link for it.
	resolveHref: (to) => (typeof to === 'string' ? `${window.location.origin}${to}` : ''),
	// the host owns the page, so leaving the island is a full page load
	navigate: (to) => {
		if (typeof to === 'string') window.location.assign(`${window.location.origin}${to}`)
	},
})

/**
 * Mount `component` with the context the host passed in.
 *
 * Load the session first, as the SPA does in its router guard. An island
 * formats numbers and dates as soon as it has rows, and a chart does not
 * re-read the reader's locale or the site's currency later. If the session
 * fails to load, the island does not mount, and the host shows the error: the
 * defaults would draw every number in the wrong locale.
 */
export async function mountIsland(component: any, el: HTMLElement, context: Record<string, any>) {
	await session.initialize()

	return mountVueIsland(el, {
		...context,
		component,
		configure: configureIsland,
	})
}
