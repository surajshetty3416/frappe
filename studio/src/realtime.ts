import { io, type Socket } from "socket.io-client"

declare global {
	interface Window {
		site_name: string
		socketio_port?: number
	}
}

type Handler = (data: { doctype: string; name: string; modified?: string }) => void

let socket: Socket | null = null
const rooms = new Map<string, number>()

function connect() {
	if (socket) return socket
	const port = window.location.port ? `:${window.socketio_port || 9000}` : ""
	const protocol = port ? "http" : "https"
	socket = io(`${protocol}://${window.location.hostname}${port}/${window.site_name}`, { withCredentials: true })
	// the server forgets a socket's rooms when it reconnects
	socket.on("connect", () => rooms.forEach((_, room) => join(room)))
	return socket
}

function join(room: string) {
	const [kind, doctype, name] = room.split("\u0000")
	if (kind === "doc") socket?.emit("doc_subscribe", doctype, name)
	else socket?.emit("doctype_subscribe", doctype)
}

function subscribe(room: string, event: string, handler: Handler) {
	const s = connect()
	rooms.set(room, (rooms.get(room) ?? 0) + 1)
	if (rooms.get(room) === 1) join(room)
	s.on(event, handler)
	return () => {
		s.off(event, handler)
		const count = (rooms.get(room) ?? 1) - 1
		if (count > 0) return void rooms.set(room, count)
		rooms.delete(room)
		const [kind, doctype, name] = room.split("\u0000")
		if (kind === "doc") s.emit("doc_unsubscribe", doctype, name)
		else s.emit("doctype_unsubscribe", doctype)
	}
}

// Frappe publishes `doc_update` to everyone who has the document open, whoever saved it
export function onDocUpdate(doctype: string, name: string, callback: (modified?: string) => void) {
	return subscribe(["doc", doctype, name].join("\u0000"), "doc_update", (data) => {
		if (data.doctype === doctype && data.name === name) callback(data.modified)
	})
}

export function onListUpdate(doctype: string, callback: (name: string) => void) {
	return subscribe(["list", doctype].join("\u0000"), "list_update", (data) => {
		if (data.doctype === doctype) callback(data.name)
	})
}
