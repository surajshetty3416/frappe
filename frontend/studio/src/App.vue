<template>
	<div class="h-full">
		<router-view v-slot="{ Component }">
			<keep-alive>
				<component :is="Component" />
			</keep-alive>
		</router-view>
	</div>
</template>

<script setup lang="ts">
import { provide } from "vue"
import { useSocket } from "@studio/socket"
import { useLiveEditor } from "@studio/utils/useLiveEditor"

provide("socket", useSocket())
useLiveEditor()
</script>
