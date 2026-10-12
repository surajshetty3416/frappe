import BuilderInput from "@builder/components/Controls/Input.vue";
import { Button, FormControl } from "frappe-ui";
import type { App } from "vue";

// many builder templates use these without importing them
export function registerGlobalComponents(app: App) {
	app.component("Button", Button);
	app.component("FormControl", FormControl);
	app.component("BuilderInput", BuilderInput);
}
