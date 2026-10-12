import { io } from "socket.io-client"

let socket = null
// socketio_port and site_name come from the page's boot data (the shell's, or the renderer template's)
export function initSocket() {
	let host = window.location.hostname
	let port = window.location.port ? `:${window.socketio_port}` : ""
	let protocol = port ? "http" : "https"
	let url = `${protocol}://${host}${port}/${window.site_name}`

	socket = io(url, {
		withCredentials: true,
		reconnectionAttempts: 5,
	})
	return socket
}

export function useSocket() {
	return socket
}
