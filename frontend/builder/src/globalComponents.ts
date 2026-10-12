import BuilderInput from "@builder/components/Controls/Input.vue";
import { Button, FormControl } from "frappe-ui";
import type { App, Component } from "vue";

// many builder templates use these without importing them; another layer may have
// registered the same frappe-ui components already
export function registerGlobalComponents(app: App) {
	const register = (name: string, component: Component) => app.component(name) || app.component(name, component);
	register("Button", Button);
	register("FormControl", FormControl);
	register("BuilderInput", BuilderInput);
}
