export function sessionUser(): string {
	const cookie = document.cookie.split("; ").find((part) => part.startsWith("user_id="))
	return cookie ? decodeURIComponent(cookie.slice("user_id=".length)) : "Guest"
}

export const isLoggedIn = () => sessionUser() !== "Guest"
