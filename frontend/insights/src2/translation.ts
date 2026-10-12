import type { App } from 'vue'

function getTranslatedMessage(message: string): string {
	// Module-scope option lists call this while they are being defined, so it
	// runs wherever a module is loaded — including a test runner with no window.
	if (typeof window === 'undefined') return message
	return window.translated_messages?.[message] || message
}

function translate(message: string): string
function translate(message: string, ...args: string[]): string
function translate(message: string, ...args: string[]): string {
	const translatedMessage = getTranslatedMessage(message)
	if (args.length === 0) {
		return translatedMessage
	}
	return translatedMessage.replace(/{(\d+)}/g, function (match, index) {
		return typeof args[index] != 'undefined' ? args[index] : match
	})
}

export const __ = translate

/**
 * A table of translated strings, built when it is first read rather than when
 * the module defining it loads.
 *
 * A module can load before the translations are set, so a `const` whose values
 * are `__()` calls could stay English for the session. This reads them at call
 * time and rebuilds when a new set arrives.
 */
export function translatedTable<T>(build: () => T): () => T {
	let messages: unknown
	let table: T | undefined
	return () => {
		const current = typeof window === 'undefined' ? undefined : window.translated_messages
		if (table === undefined || messages !== current) {
			messages = current
			table = build()
		}
		return table
	}
}

/**
 * Install this app's `__` for an island's templates.
 *
 * A host can bring its own `__`. Desk gives an island `frappe._` through
 * `SetVueGlobals`. That one replaces `{0}` only when it gets an object of
 * replacements. Insights passes arguments positionally, so with desk's `__` the
 * `{0}` would show on the page as is. In the SPA the shell's `__` takes an array
 * of replacements, so a template that passes arguments imports this module's.
 */
export function installTranslate(app: App<Element>) {
	app.config.globalProperties.__ = translate
}
