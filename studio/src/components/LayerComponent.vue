<template>
	<!-- a layer's styles reach only inside its own data-layer -->
	<div :data-layer="layer" class="contents">
		<component :is="mount.component" v-bind="mount.props ?? {}" />
	</div>
</template>

<script setup lang="ts">
import type { LayerComponent } from "../editor"

defineProps<{ mount: LayerComponent; layer?: string }>()
</script>
