import { useColorScheme } from "frappe-ui";
import { computed } from "vue";

// the shell owns the color scheme, so the editor reads and flips that one
export function useDarkMode() {
	const { resolvedColorScheme, toggleColorScheme } = useColorScheme();
	return {
		isDark: computed(() => resolvedColorScheme.value === "dark"),
		toggleDark: toggleColorScheme,
	};
}
