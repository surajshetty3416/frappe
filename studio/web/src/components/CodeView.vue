<template>
	<div class="min-h-0 flex-1 overflow-auto rounded-4 border border-outline-gray-2 text-sm">
		<div v-if="error" class="p-3 text-ink-red-4">{{ error }}</div>
		<Codemirror v-else :model-value="shown" :extensions="extensions" disabled />
	</div>
</template>

<script setup lang="ts">
import { css } from "@codemirror/lang-css"
import { html } from "@codemirror/lang-html"
import { javascript } from "@codemirror/lang-javascript"
import { python } from "@codemirror/lang-python"
import { EditorView } from "@codemirror/view"
import { tomorrow } from "thememirror"
import { computed, ref, watch } from "vue"
import { Codemirror } from "vue-codemirror"

// a part of the artifact as read-only code, a tab of the shell's Code drawer: `code` as given,
// or what `load` gets from the server, again whenever `version` changes
const props = defineProps<{
	code?: string
	load?: () => Promise<string>
	version?: string
	language: "html" | "css" | "javascript" | "python"
}>()

const LANGUAGES = { html, css, javascript, python }
const extensions = computed(() => [LANGUAGES[props.language](), tomorrow, EditorView.lineWrapping])

const loaded = ref("")
const error = ref("")
const shown = computed(() => props.code ?? loaded.value)
watch(
	() => props.version,
	async () => {
		if (!props.load) return
		error.value = ""
		try {
			loaded.value = await props.load()
		} catch (e) {
			error.value = (e as Error)?.message || "Could not load the code"
		}
	},
	{ immediate: true },
)
</script>
