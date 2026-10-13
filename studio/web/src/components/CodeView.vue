<template>
	<div class="min-h-0 flex-1 overflow-auto rounded-4 border border-outline-gray-2 text-sm">
		<Codemirror :model-value="code" :extensions="extensions" disabled />
	</div>
</template>

<script setup lang="ts">
import { css } from "@codemirror/lang-css"
import { html } from "@codemirror/lang-html"
import { javascript } from "@codemirror/lang-javascript"
import { python } from "@codemirror/lang-python"
import { EditorView } from "@codemirror/view"
import { tomorrow } from "thememirror"
import { computed } from "vue"
import { Codemirror } from "vue-codemirror"

// a part of the artifact as read-only code, a tab of the shell's Code drawer
const props = defineProps<{ code: string; language: "html" | "css" | "javascript" | "python" }>()

const LANGUAGES = { html, css, javascript, python }
const extensions = computed(() => [LANGUAGES[props.language](), tomorrow, EditorView.lineWrapping])
</script>
