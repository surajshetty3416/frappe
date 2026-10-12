import { createResource } from "frappe-ui";

let codeCompletions = createResource({
	url: "frappe.web.api.get_codemirror_completions",
	method: "GET",
	auto: true,
});

export default codeCompletions;
