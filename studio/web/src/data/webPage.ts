import { createListResource } from "frappe-ui";

const webPages = createListResource({
	method: "GET",
	doctype: "Builder Page",
	fields: ["name", "route", "page_name", "page_title", "published", "modified"],
	filters: { is_template: 0 },
	orderBy: "modified desc",
	auto: true,
	cache: "pages",
	pageLength: 50,
});

export { webPages };
