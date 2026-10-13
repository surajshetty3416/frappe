<template>
	<div class="flex h-full flex-col gap-2">
		<div class="flex items-center gap-1">
			<span class="text-sm text-ink-gray-5">JavaScript</span>
			<span v-if="dirty" class="text-sm text-ink-amber-5">· Not applied</span>
			<div class="ml-auto flex items-center gap-1">
				<Popover side="bottom" align="end" :offset="6" bare>
					<template #trigger>
						<Button variant="ghost" icon="lucide-circle-help" tooltip="How to write the page script" />
					</template>
					<div class="max-w-sm rounded-4 border border-outline-gray-2 bg-surface-base p-3 shadow-lg">
						<PageScriptHelp />
					</div>
				</Popover>
				<Button :loading="saving" :disabled="!dirty" label="Apply" icon-left="lucide-check" @click="saveScript" />
			</div>
		</div>
		<ErrorMessage v-if="scriptError" :message="scriptError" />
		<div class="relative min-h-0 flex-1 overflow-hidden rounded-4 border border-outline-gray-2">
			<Code
				:modelValue="script"
				language="javascript"
				height="100%"
				maxHeight="100%"
				:emitOnChange="true"
				valueMode="text"
				:borderless="true"
				placeholder="// Runs when the page loads"
				:completions="completions"
				@update:modelValue="onChange"
				@save="saveScript"
			/>
		</div>
	</div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from "vue"
import { toast, Button, Popover, ErrorMessage } from "frappe-ui"
import Code from "@ui/components/Code.vue"
import PageScriptHelp from "@ui/components/PageScriptHelp.vue"
import { getScriptError } from "@ui/utils/parseCode"
import { useStudioCompletions } from "@ui/utils/completions/useStudioCompletions"
import { usePageScope } from "@ui/stores/codeStore"
import useStudioStore from "@ui/stores/studioStore"

const store = useStudioStore()
const pageScope = usePageScope()
const completions = useStudioCompletions(true, true)

const savedScript = computed(() => store.activePage?.script || "")

const script = ref(savedScript.value)
const saving = ref(false)
const scriptError = ref<string | null>(null)
const dirty = computed(() => script.value !== savedScript.value)

// Reset when switching pages.
watch([() => store.activePage?.name, savedScript], () => {
	script.value = savedScript.value
	scriptError.value = null
})

function onChange(value: string) {
	// the editor also emits on blur, so clicking Save must not wipe the error it is about to show
	if (value !== script.value) scriptError.value = null
	script.value = value
}

async function saveScript() {
	// A broken script fails to compile and takes down every binding on the page, so block it.
	const syntaxError = getScriptError(script.value)
	if (syntaxError) {
		const hint = script.value.includes("{{")
			? " Scripts are plain JavaScript — use expressions directly, not {{ }} interpolation."
			: ""
		scriptError.value = `${syntaxError.message}.${hint}`
		return
	}
	saving.value = true
	try {
		await store.updateActivePage("script", script.value)
		// keep the runtime bindings in sync with the saved script
		pageScope.setPageScript(store.activePage!)
		toast.success("Applied the page script")
	} catch (error: any) {
		toast.error("Failed to save the page script", { description: error?.messages?.join(", ") })
	} finally {
		saving.value = false
	}
}
</script>
