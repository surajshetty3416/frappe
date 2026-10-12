import { __ } from "@shell/translation";

export { __ };

declare module "@vue/runtime-core" {
	interface ComponentCustomProperties {
		__: typeof __;
	}
}
