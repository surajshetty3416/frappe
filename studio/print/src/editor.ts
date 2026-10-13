// A Print Format in Studio's editor shell: the HTML canvas with print output, a page of its
// real size rendered by the print view against a record.
import { defineOutputEditor } from "@web/output/outputEditor"

import PrintDetails from "./PrintDetails.vue"

const query = (params: Record<string, string>) => new URLSearchParams(params).toString()

function links(format: string, doctype: string | null, record: string | null) {
	if (!doctype || !record) return null
	const params = { doctype, name: record, format }
	return {
		view: `/printview?${query({ ...params, trigger_print: "0" })}`,
		pdf: `/api/method/frappe.utils.print_format.download_pdf?${query(params)}`,
	}
}

export default defineOutputEditor({
	doctype: "Print Format",
	param: "format",
	route: (name) => `/studio/print/format/${encodeURIComponent(name)}`,
	status: (state) =>
		state.doc?.disabled ? { label: "Disabled", theme: "gray" } : { label: "Enabled", theme: "green" },
	primaryAction(state) {
		const urls = links(state.name, state.target, state.record)
		if (!urls) return null
		return {
			label: "Download PDF",
			icon: "lucide-download",
			run: async () => void window.open(urls.pdf, "_blank"),
		}
	},
	details(state) {
		const doc = state.doc!
		const page = state.page
		const urls = links(state.name, state.target, state.record)
		return [
			{ label: "Prints", value: String(doc.doc_type ?? "") },
			{ label: "Margins", value: page ? `${page.margins.top} mm` : "" },
			...(urls
				? [
						{ label: "Print view", value: "Open", href: urls.view },
						{ label: "PDF", value: "Download", href: urls.pdf },
					]
				: []),
		]
	},
	detailsForm: PrintDetails,
	code: [
		{ name: "html", label: "HTML" },
		{ name: "css", label: "CSS" },
	],
})
