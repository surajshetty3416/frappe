// An Email Template in Studio's editor shell: the HTML canvas with email output, the subject
// and the email rendered against a record.
import { call, toast } from "frappe-ui"

import { defineOutputEditor } from "@web/output/outputEditor"

import EmailDetails from "./EmailDetails.vue"

export default defineOutputEditor({
	doctype: "Email Template",
	param: "template",
	route: (name) => `/studio/email/template/${encodeURIComponent(name)}`,
	status: (state) =>
		state.senders.length
			? { label: state.senders.join(", "), theme: "green" }
			: { label: "Not sent automatically", theme: "gray" },
	primaryAction(state) {
		return {
			label: "Send test",
			icon: "lucide-send",
			disabled: !state.doc,
			run: async () => {
				const recipient = await call("frappe.web.output.email_template.send_test", {
					template: state.name,
					record: state.record,
				})
				toast.success(`Test sent to you (${recipient})`)
			},
		}
	},
	details(state) {
		const doc = state.doc!
		return [{ label: "Rendered against", value: String(doc.reference_doctype || "Any record") }]
	},
	detailsForm: EmailDetails,
	code: (state) => [{ name: "html", label: "HTML", code: String(state.doc?.response_html ?? ""), language: "html" }],
})
