import { call } from "frappe-ui"

export interface Person {
	name: string
	email: string
	full_name: string
	user_image: string | null
	enabled: 0 | 1
	last_login: string | null
	roles: string[]
}

// the framework gives these to users by itself, so nobody picks them
const AUTOMATIC_ROLES = ["Administrator", "Guest", "All", "Desk User"]

export async function getPeople(): Promise<Person[]> {
	const [users, roles] = await Promise.all([
		call("frappe.client.get_list", {
			doctype: "User",
			fields: ["name", "email", "full_name", "user_image", "enabled", "last_login"],
			filters: { name: ["!=", "Guest"] },
			order_by: "creation asc",
			limit_page_length: 0,
		}),
		call("frappe.client.get_list", {
			doctype: "Has Role",
			parent: "User",
			fields: ["parent", "role"],
			filters: { parenttype: "User", role: ["not in", AUTOMATIC_ROLES] },
			order_by: "role asc",
			limit_page_length: 0,
		}),
	])
	return users.map((user: Omit<Person, "roles">) => ({
		...user,
		roles: roles.filter((row: { parent: string }) => row.parent === user.name).map((row: { role: string }) => row.role),
	}))
}

export async function getRoles(): Promise<string[]> {
	const roles = await call("frappe.client.get_list", {
		doctype: "Role",
		fields: ["name"],
		filters: { disabled: 0, name: ["not in", AUTOMATIC_ROLES] },
		order_by: "name asc",
		limit_page_length: 0,
	})
	return roles.map((role: { name: string }) => role.name)
}

export async function invite(email: string, roles: string[]) {
	await call("frappe.client.insert", {
		doc: {
			doctype: "User",
			email,
			first_name: email.split("@")[0],
			send_welcome_email: 1,
			roles: roles.map((role) => ({ role })),
		},
	})
}

export async function setRoles(user: string, roles: string[]) {
	const doc = await call("frappe.client.get", { doctype: "User", name: user })
	const automatic = doc.roles.filter((row: { role: string }) => AUTOMATIC_ROLES.includes(row.role))
	doc.roles = [...automatic, ...roles.map((role) => ({ role }))]
	await call("frappe.client.save", { doc })
}

// an invited person has no name of their own until they sign in
export const displayName = (person: Person) => (person.last_login ? person.full_name || person.name : person.email)

// one toast slot for the page, so a new message replaces the last instead of stacking on it
export const toastOptions = { id: "settings" }

// the server's own message, without the HTML it wraps names in
export function errorMessage(error: unknown) {
	const { messages, message } = error as { messages?: string[]; message?: string }
	const text = messages?.at(-1) || message || "Something went wrong"
	return new DOMParser().parseFromString(text, "text/html").body.textContent || text
}
