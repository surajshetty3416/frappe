import { io, type Socket } from "socket.io-client";

declare global {
	interface Window {
		site_name: string;
		socketio_port?: number;
	}
}

// The FrappeUI plugin used to open this connection and hang it off
// `app.config.globalProperties.$socket`. It no longer does, so the one consumer
// (RealTimeHandler) opens it here instead.
export function createSocket(): Socket {
	const host = window.location.hostname;
	const port = window.location.port ? `:${window.socketio_port || 9000}` : "";
	const protocol = port ? "http" : "https";
	return io(`${protocol}://${host}${port}/${window.site_name}`, { withCredentials: true });
}
