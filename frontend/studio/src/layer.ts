import { defineLayer } from "@shell/layer"
import { h } from "vue"

// placeholder until the layer is ported onto the shell
export default defineLayer({
	name: "studio",
	title: "Apps",
	icon: "lucide-blocks",
	path: "/studio",
	component: async () => ({ render: () => h("div", { class: "p-8 text-ink-gray-6" }, "Apps is being ported") }),
	routes: [],
})
