<template>
	<div>
		<div class="col-md-6" v-for="option in options" :key="option">
			<label :for="option">
				<input type="checkbox" :value="option" :id="option" :checked="is_checked(option)"/>
				<span class="label-area small">{{ option }}</span>
			</label>
		</div>
	</div>
</template>
<script>
export default {
	props: ['options', 'selected_items'],
	methods: {
		is_checked(option) {
			return this.selected_items.includes(option)
		}
	}
}
</script>
