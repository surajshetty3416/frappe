import type { App } from "vue"

declare global {
	interface Window {
		translated_messages?: Record<string, string>
		__: typeof __
	}
}

export function __(message: string, replace?: (string | number)[], context?: string) {
	const messages = window.translated_messages || {}
	let translated = (context && messages[`${message}:${context}`]) || messages[message] || message
	replace?.forEach((value, index) => {
		translated = translated.replaceAll(`{${index}}`, String(value))
	})
	return translated
}

export default {
	install(app: App) {
		app.config.globalProperties.__ = __
		window.__ = __
	},
}
