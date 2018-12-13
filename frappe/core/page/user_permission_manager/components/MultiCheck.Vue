<template>
	<div>
		<div v-for="option in options" :key="option">
			<input type="checkbox" :value="option"/>
			<label>{{ option }}</label>
		</div>
	</div>
</template>
<script>
export default {
	props: ['options']
}
</script>
