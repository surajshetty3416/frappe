<template>
	<SettingsHeader title="Email" description="The account invites, alerts and automations send from.">
		<template #actions>
			<Button label="Send test email" :disabled="!saved || dirty" :loading="sending" @click="sendTest" />
			<Button variant="solid" label="Save" :disabled="!dirty || !valid" :loading="saving" @click="save" />
		</template>
	</SettingsHeader>
	<SettingsBody>
		<div v-if="loading" class="flex h-24 items-center justify-center">
			<LoadingIndicator class="size-4 text-ink-gray-4" />
		</div>
		<div v-else class="mt-4 divide-y divide-outline-gray-1">
			<SettingsRow title="From name" description="Shown as the sender.">
				<TextInput v-model="form.email_account_name" class="w-64" placeholder="Frappeverse" />
			</SettingsRow>
			<SettingsRow title="Email address">
				<TextInput v-model="form.email_id" type="email" class="w-64" placeholder="hello@example.com" />
			</SettingsRow>
			<SettingsRow title="SMTP server">
				<TextInput v-model="form.smtp_server" class="w-64" placeholder="smtp.example.com" />
			</SettingsRow>
			<SettingsRow title="Port">
				<TextInput v-model="form.smtp_port" class="w-64" placeholder="587" />
			</SettingsRow>
			<SettingsRow title="Security">
				<Select v-model="form.security" class="w-64" :options="securityOptions" />
			</SettingsRow>
			<SettingsRow title="Login" description="Leave empty to sign in with the email address.">
				<TextInput v-model="form.login_id" class="w-64" :placeholder="form.email_id || 'Email address'" />
			</SettingsRow>
			<SettingsRow title="Password" :description="saved ? 'Leave empty to keep the saved one.' : 'Studio checks the connection when you save.'">
				<Password v-model="form.password" class="w-64" :placeholder="saved ? 'Saved' : ''" />
			</SettingsRow>
		</div>
	</SettingsBody>
</template>

<script setup lang="ts">
import { Button, LoadingIndicator, Password, Select, SettingsBody, SettingsHeader, SettingsRow, TextInput, call, toast } from "frappe-ui"
import { computed, reactive, ref } from "vue"

import { errorMessage } from "./people"

const securityOptions = [
	{ label: "STARTTLS", value: "tls" },
	{ label: "SSL/TLS", value: "ssl" },
	{ label: "None", value: "none" },
]

const blank = () => ({
	email_account_name: "",
	email_id: "",
	smtp_server: "",
	smtp_port: "587",
	security: "tls",
	login_id: "",
	password: "",
})

const form = reactive(blank())
const saved = ref<string | null>(null)
const snapshot = ref("")
const loading = ref(true)
const saving = ref(false)
const sending = ref(false)

const dirty = computed(() => JSON.stringify(form) !== snapshot.value)
const valid = computed(() => form.email_account_name.trim() && /^\S+@\S+\.\S+$/.test(form.email_id) && form.smtp_server.trim())

async function load() {
	const [account] = await call("frappe.client.get_list", {
		doctype: "Email Account",
		fields: ["name"],
		filters: { enable_outgoing: 1 },
		order_by: "default_outgoing desc, creation asc",
		limit_page_length: 1,
	})
	Object.assign(form, blank())
	saved.value = account?.name ?? null
	if (account) {
		const doc = await call("frappe.client.get", { doctype: "Email Account", name: account.name })
		Object.assign(form, {
			email_account_name: doc.email_account_name || doc.name,
			email_id: doc.email_id || "",
			smtp_server: doc.smtp_server || "",
			smtp_port: doc.smtp_port || "",
			security: doc.use_ssl_for_outgoing ? "ssl" : doc.use_tls ? "tls" : "none",
			login_id: doc.login_id_is_different ? doc.login_id || "" : "",
		})
	}
	snapshot.value = JSON.stringify(form)
	loading.value = false
}
load()

async function save() {
	const values: Record<string, unknown> = {
		email_account_name: form.email_account_name.trim(),
		email_id: form.email_id.trim(),
		smtp_server: form.smtp_server.trim(),
		smtp_port: form.smtp_port.trim(),
		use_tls: form.security === "tls" ? 1 : 0,
		use_ssl_for_outgoing: form.security === "ssl" ? 1 : 0,
		login_id_is_different: form.login_id.trim() ? 1 : 0,
		login_id: form.login_id.trim(),
		enable_outgoing: 1,
		default_outgoing: 1,
		always_use_account_name_as_sender_name: 1,
	}
	if (form.password) values.password = form.password
	saving.value = true
	try {
		if (saved.value) {
			const doc = await call("frappe.client.get", { doctype: "Email Account", name: saved.value })
			await call("frappe.client.save", { doc: { ...doc, ...values } })
		} else {
			await call("frappe.client.insert", { doc: { doctype: "Email Account", ...values } })
		}
	} catch (error) {
		return toast.error(errorMessage(error))
	} finally {
		saving.value = false
	}
	toast.success("Email account saved")
	load()
}

async function sendTest() {
	sending.value = true
	try {
		const recipient = await call("frappe.settings.api.send_test_email", { email_account: saved.value })
		toast.success(`Sent a test email to ${recipient}`)
	} catch (error) {
		toast.error(errorMessage(error))
	} finally {
		sending.value = false
	}
}
</script>
