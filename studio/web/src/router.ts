import { sessionUser as currentUser } from "@shell/session";
import { call } from "frappe-ui";
import { ref } from "vue";
import type { Router } from "vue-router";
import { __ } from "./translation";

const sessionUser = ref(currentUser());

// The shell owns the app's one router. The layer's setup hands it over before any module
// that imports it runs, and `export { router as default }` keeps the import a live binding.
let router: Router;

export function setAppRouter(appRouter: Router) {
	router = appRouter;
}

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

export { router as default, sessionUser };
