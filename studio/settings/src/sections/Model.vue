<template>
	<SettingsHeader title="AI model" description="The model the assistant thinks with.">
		<template #actions>
			<Button variant="solid" label="Save" :disabled="!dirty || !form.model.trim()" :loading="saving" @click="save" />
		</template>
	</SettingsHeader>
	<SettingsBody>
		<div v-if="loading" class="flex h-24 items-center justify-center">
			<LoadingIndicator class="size-4 text-ink-gray-4" />
		</div>
		<div v-else class="mt-4 divide-y divide-outline-gray-1">
			<SettingsRow title="Provider">
				<Select v-model="form.provider" class="w-64" :options="providers" @update:model-value="pickProvider" />
			</SettingsRow>
			<SettingsRow title="Model">
				<Select v-if="isClaudeCode" v-model="form.model" class="w-64" :options="claudeCodeModels" />
				<TextInput v-else v-model="form.model" class="w-64" placeholder="claude-opus-4-1" />
			</SettingsRow>
			<SettingsRow title="Reasoning effort" description="Higher is more thorough, and slower.">
				<Select v-model="form.effort" class="w-64" :options="efforts" />
			</SettingsRow>
			<SettingsRow
				:title="isClaudeCode ? 'Claude Code token' : 'API key'"
				:description="isClaudeCode ? 'Optional. Leave empty when the Claude Code CLI on the server is logged in.' : ''"
			>
				<div class="flex items-center gap-2">
					<Button v-if="hasToken && !form.token" variant="ghost" label="Remove" @click="removeToken" />
					<Password
						v-model="form.token"
						class="w-64"
						:placeholder="hasToken ? 'Saved' : isClaudeCode ? 'Uses the CLI login' : ''"
					/>
				</div>
			</SettingsRow>
		</div>
	</SettingsBody>
</template>

<script setup lang="ts">
import { Button, LoadingIndicator, Password, Select, SettingsBody, SettingsHeader, SettingsRow, TextInput, call, toast } from "frappe-ui"
import { computed, reactive, ref } from "vue"

import { errorMessage } from "./people"

// the assistant's Flow Agent, made on install
const ASSISTANT = "Flow"
const CLAUDE_CODE = "claude-code"

const providers = [
	{ label: "Claude Code", value: CLAUDE_CODE },
	{ label: "Anthropic", value: "anthropic" },
	{ label: "OpenAI", value: "openai" },
	{ label: "OpenRouter", value: "openrouter" },
	{ label: "Google Gemini", value: "gemini" },
]
const claudeCodeModels = [
	{ label: "Opus", value: "opus" },
	{ label: "Sonnet", value: "sonnet" },
	{ label: "Haiku", value: "haiku" },
]
const efforts = ["off", "minimal", "low", "medium", "high", "xhigh", "max"].map((value) => ({
	label: value === "xhigh" ? "Extra high" : value[0].toUpperCase() + value.slice(1),
	value,
}))

const form = reactive({ provider: CLAUDE_CODE, model: "opus", effort: "high", token: "" })
const flowModel = ref("")
const hasToken = ref(false)
const snapshot = ref("")
const loading = ref(true)
const saving = ref(false)

const isClaudeCode = computed(() => form.provider === CLAUDE_CODE)
const dirty = computed(() => JSON.stringify(form) !== snapshot.value)

async function load() {
	const agent = await call("frappe.client.get_value", {
		doctype: "Flow Agent",
		filters: ASSISTANT,
		fieldname: ["model", "reasoning_effort"],
	})
	flowModel.value = agent.model
	const model = await call("frappe.client.get_value", {
		doctype: "Flow Model",
		filters: agent.model,
		fieldname: ["provider", "model_id"],
	})
	Object.assign(form, {
		provider: model.provider,
		model: model.model_id.replace(`${model.provider}/`, ""),
		effort: agent.reasoning_effort || "high",
		token: "",
	})
	await loadToken()
	snapshot.value = JSON.stringify(form)
	loading.value = false
}
load()

async function loadToken() {
	const [provider] = await call("frappe.client.get_list", {
		doctype: "Flow Provider",
		fields: ["api_key"],
		filters: { name: form.provider },
	})
	hasToken.value = Boolean(provider?.api_key)
}

function pickProvider() {
	form.model = isClaudeCode.value ? "opus" : ""
	form.token = ""
	loadToken()
}

const setToken = (value: string) =>
	call("frappe.client.set_value", { doctype: "Flow Provider", name: form.provider, fieldname: "api_key", value })

async function removeToken() {
	await setToken("")
	toast.success(isClaudeCode.value ? "Token removed. The assistant uses the CLI login." : "API key removed")
	loadToken()
}

async function save() {
	saving.value = true
	try {
		const exists = await call("frappe.client.get_count", { doctype: "Flow Provider", filters: { name: form.provider } })
		if (!exists) await call("frappe.client.insert", { doc: { doctype: "Flow Provider", provider: form.provider } })
		if (form.token) await setToken(form.token)
		await call("frappe.client.set_value", {
			doctype: "Flow Model",
			name: flowModel.value,
			fieldname: { provider: form.provider, model_id: `${form.provider}/${form.model.trim()}` },
		})
		await call("frappe.client.set_value", {
			doctype: "Flow Agent",
			name: ASSISTANT,
			fieldname: "reasoning_effort",
			value: form.effort,
		})
	} catch (error) {
		return toast.error(errorMessage(error))
	} finally {
		saving.value = false
	}
	toast.success("AI model saved")
	load()
}
</script>
