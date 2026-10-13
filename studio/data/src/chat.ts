// The shell has no call yet for an editor to send the chat beside it a message, so this types
// the message into that chat's composer and presses Enter, as a person would.
export function askChat(message: string) {
	const composer = document.querySelector<HTMLTextAreaElement>('[data-layer="ai"] textarea')
	if (!composer || composer.disabled) return false
	composer.value = message
	composer.dispatchEvent(new Event("input", { bubbles: true }))
	composer.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true, cancelable: true }))
	return true
}
