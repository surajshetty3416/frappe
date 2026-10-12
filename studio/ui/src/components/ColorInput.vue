<!-- Extracted from Builder -->
<template>
	<ColorPicker
		:modelValue="modelValue"
		@update:modelValue="(color) => emit('update:modelValue', color)"
		:property="property"
	>
		<template #target="{ togglePopover, isOpen }">
			<div class="flex items-center justify-between">
				<InputLabel v-if="label">{{ label }}</InputLabel>
				<div class="relative w-full">
					<Input
						type="text"
						class="[&>div>input]:pl-8"
						placeholder="Set Color"
						:modelValue="displayValue"
						:disabled="disabled"
						@update:modelValue="
							(value: string | null) => {
								value = getRGB(value)
								emit('update:modelValue', value)
							}
						"
					>
						<template #prefix>
							<div
								class="h-4 w-4 rounded-4 shadow-sm"
								@click="togglePopover"
								:style="{
									background: modelValue
										? modelValue
										: `url(${colorCircle}) center / contain`,
								}"
							></div>
						</template>
					</Input>
				</div>
			</div>
		</template>
	</ColorPicker>
</template>
<script setup lang="ts">
import { computed } from "vue"
import ColorPicker from "@ui/components/ColorPicker.vue"
import Input from "@ui/components/Input.vue"
import InputLabel from "@ui/components/InputLabel.vue"
import { getColorFromToken, getRGB, isColorToken } from "@ui/utils/helpers"
import type { HashString } from "@ui/types"

// a public file, so app builds that bundle this editor component don't have to resolve it
const colorCircle = `${import.meta.env.BASE_URL}studio-color-circle.png`

const props = withDefaults(
	defineProps<{
		modelValue?: HashString | null
		label?: string
		property?: "backgroundColor" | "borderColor" | "textColor"
	}>(),
	{
		modelValue: null,
		property: "textColor",
	},
)
const emit = defineEmits(["update:modelValue"])

const displayValue = computed(() => {
	if (!props.modelValue) return ""
	return getColorFromToken(props.modelValue)
})

const disabled = computed(() => isColorToken(props.modelValue))
</script>
