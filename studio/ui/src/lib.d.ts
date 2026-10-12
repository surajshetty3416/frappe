
// Page globals: the shell's boot data in the editor, the renderer template's in a studio app
interface Window {
	site_name: string
	site_url: string
	socketio_port?: number
	is_developer_mode?: boolean
	is_preview?: boolean
	__APP_COMPONENTS__: any
}
