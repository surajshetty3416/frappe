frappe.pages["insights"].on_page_load = function (wrapper) {
	window.location.href = frappe.boot.insights_path || "/studio/analytics";
};
