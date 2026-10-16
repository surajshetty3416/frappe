import { call, useColorScheme } from "frappe-ui"

// the shell's light or dark, kept on the user as well, so the desk's forms open in the same one
export function useSharedColorScheme() {
	const { resolvedColorScheme, toggleColorScheme } = useColorScheme()
	function toggle() {
		toggleColorScheme()
		call("frappe.core.doctype.user.user.switch_theme", {
			theme: resolvedColorScheme.value === "dark" ? "Dark" : "Light",
		}).catch(() => {})
	}
	return { resolvedColorScheme, toggleColorScheme: toggle }
}
