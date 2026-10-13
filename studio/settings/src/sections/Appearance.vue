<template>
	<SettingsHeader title="Appearance" description="How Studio looks on this device." />
	<SettingsBody>
		<div class="mt-4">
			<SettingsRow title="Theme" description="System follows your computer's setting.">
				<TabButtons :model-value="colorScheme" :options="schemes" @update:model-value="setColorScheme" />
			</SettingsRow>
		</div>
	</SettingsBody>
</template>

<script setup lang="ts">
import { type ColorScheme, SettingsBody, SettingsHeader, SettingsRow, TabButtons, useColorScheme } from "frappe-ui"

const { colorScheme, setColorScheme: setScheme } = useColorScheme()
const setColorScheme = (value: string | number) => setScheme(value as ColorScheme)
const schemes = [
	{ label: "Light", value: "light", iconLeft: "lucide-sun" },
	{ label: "Dark", value: "dark", iconLeft: "lucide-moon" },
	{ label: "System", value: "system", iconLeft: "lucide-monitor" },
]
</script>
