import { defineLayer } from "@shell/layer"
import { h } from "vue"

// placeholder until the layer is ported onto the shell
export default defineLayer({
	name: "insights",
	title: "Dashboards",
	icon: "lucide-chart-column",
	path: "/insights",
	component: async () => ({ render: () => h("div", { class: "p-8 text-ink-gray-6" }, "Dashboards is being ported") }),
	routes: [],
})
