<template>
	<div data-layer="ai" class="flex h-full min-h-0 flex-col bg-surface-base text-base text-ink-gray-8">
		<div v-if="!store" class="flex flex-1 items-center justify-center">
			<LoadingIndicator class="size-4 text-ink-gray-5" />
		</div>
		<template v-else>
			<div v-if="blank" class="flex min-h-0 flex-1 flex-col items-center justify-end px-6 pb-6 text-center">
				<p class="text-base font-medium text-ink-gray-8">Try {{ title }}</p>
				<p class="mt-1 max-w-sm text-sm text-ink-gray-5">Send it a message as a person or an automation would. It works on this site's real records.</p>
			</div>
			<MessageList v-else />
			<Composer />
			<div v-if="blank" class="flex-1" />
		</template>
	</div>
</template>

<script setup>
// The main chat's own pieces (its store, client, transcript and composer), on a session with
// this agent instead of the assistant. Chat.vue cannot host it: it starts sessions with the
// assistant only, and renders its menu into the shell's top bar beside the main chat's.
import { computed, onBeforeUnmount, provide, shallowRef, watch } from "vue"
import { LoadingIndicator, toast } from "frappe-ui"
import Composer from "@flow/ui-core/components/Composer.vue"
import MessageList from "@flow/ui-core/components/MessageList.vue"
import { createFlowStore } from "@flow/ui-core/store.js"
import "@ai/index.css"
import { FrappeClient } from "@ai/api/client.js"
import * as transport from "@ai/api/frappe.js"
import { connectSocket } from "@ai/api/socket.js"
import { loadBoot } from "@ai/boot.js"
import { presentTool } from "@ai/chat/toolMeta.js"

const props = defineProps({
	agent: { type: String, required: true },
	title: { type: String, required: true },
	// the agent's last change; a session keeps the tools and instructions it started with
	modified: { type: String, required: true },
})

class AgentClient extends FrappeClient {
	async createSession(config = {}) {
		const data = await this.transport.call("frappe.ai.api.create_session", {
			agent: props.agent,
			title: `Test of ${props.title}`,
			auto_approve: config.auto_approve ? 1 : 0,
		})
		this.hooks.onSession?.(data)
		return { session_id: data.name, config: { ...this.sessionInfo(data).config, model: data.model } }
	}
}

const storageKey = (user) => `studio.agent-test.${user}`
const saved = () => JSON.parse(localStorage.getItem(`studio.agent-test.${props.agent}`) || "null")

const store = shallowRef(null)
let socket = null
const flow = {}
provide("flow", flow)

async function mount() {
	const boot = await loadBoot()
	socket = connectSocket(boot)
	const key = storageKey(boot.user?.name ?? "user")
	// a test asks before its agent writes, unless the person chose otherwise
	if (!localStorage.getItem(`${key}.prefs`)) localStorage.setItem(`${key}.prefs`, JSON.stringify({ mode: "ask" }))
	const client = new AgentClient({ socket, boot, transport })
	const created = createFlowStore(client, { storageKey: key, presentTool, placeholder: `Message ${props.title}…` })
	Object.assign(flow, created)
	watch(
		() => created.state.toast,
		(item) => item && (item.kind === "error" ? toast.error(item.message) : toast.success(item.message))
	)
	watch(
		() => created.state.sessionId,
		(session) => session && localStorage.setItem(`studio.agent-test.${props.agent}`, JSON.stringify({ session, modified: props.modified }))
	)
	const last = saved()
	if (last?.modified === props.modified) await created.openSession(last.session)
	store.value = created
}
mount()

const blank = computed(() => !store.value?.state.sessionId && !store.value?.state.conversation.sending.length)

function restart() {
	localStorage.removeItem(`studio.agent-test.${props.agent}`)
	store.value?.startNewChat()
}
// a changed agent starts a fresh test
watch(() => props.modified, restart)
defineExpose({ restart })

onBeforeUnmount(() => {
	store.value?.detach()
	socket?.disconnect()
})
</script>
