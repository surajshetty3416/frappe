import { call } from "frappe-ui";
import { __ } from "./translation";

let canWritePages: Promise<boolean> | null = null;

export async function validateVisit() {
	canWritePages ??= call<{ has_permission: boolean }>("frappe.client.has_permission", {
		doctype: "Builder Page",
		docname: "",
		perm_type: "write",
	})
		.then((response) => Boolean(response.has_permission))
		.catch(() => false);
	if (await canWritePages) return;
	alert(__("You do not have permission to access this page"));
	window.location.href = "/desk";
	return false;
}
