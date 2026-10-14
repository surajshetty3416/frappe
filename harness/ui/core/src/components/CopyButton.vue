<template>
	<button
		type="button"
		class="grid size-7 flex-none place-items-center rounded-4 text-ink-gray-5 hover:bg-surface-gray-2 hover:text-ink-gray-8"
		:title="copied ? 'Copied' : title"
		:style="copied ? { opacity: 1 } : undefined"
		@click.stop="copy"
	>
		<span :class="copied ? 'lucide-check' : 'lucide-copy'" class="size-3.5" />
	</button>
</template>

<script setup>
import { onBeforeUnmount, ref } from "vue"

const props = defineProps({
	text: { type: String, required: true },
	title: { type: String, default: "Copy" },
})

const copied = ref(false)
let timer = null

async function copy() {
	if (!(await writeText(props.text))) return
	copied.value = true
	clearTimeout(timer)
	timer = setTimeout(() => (copied.value = false), 2000)
}

// the Clipboard API needs a secure context: plain http (a bench, a LAN address) falls
// back to the copy command
async function writeText(text) {
	try {
		await navigator.clipboard.writeText(text)
		return true
	} catch {
		const active = document.activeElement
		const field = document.createElement("textarea")
		field.value = text
		field.style.cssText = "position: fixed; opacity: 0"
		document.body.append(field)
		field.select()
		const done = document.execCommand?.("copy")
		field.remove()
		active?.focus?.()
		return done
	}
}

onBeforeUnmount(() => clearTimeout(timer))
</script>
