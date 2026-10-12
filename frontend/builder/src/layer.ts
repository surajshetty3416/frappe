import { defineLayer } from "@shell/layer"
import { h } from "vue"

// placeholder until the layer is ported onto the shell
export default defineLayer({
	name: "builder",
	title: "Websites",
	icon: "lucide-globe",
	path: "/builder",
	component: async () => ({ render: () => h("div", { class: "p-8 text-ink-gray-6" }, "Websites is being ported") }),
	routes: [],
})
