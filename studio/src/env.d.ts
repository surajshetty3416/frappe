// boot data the shell reads; each layer declares its own keys where it reads them
declare global {
	interface Window {
		flow_boot?: { models?: unknown[] }
	}
}

export {}
