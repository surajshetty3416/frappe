<template>
	<div>
		<div class="col-md-6" v-for="option in options" :key="option">
			<label>
				<input type="checkbox" :value="option" :id="option" :checked="value.includes(option)" @change="update(option)"/>
				<span class="label-area small">{{ option }}</span>
			</label>
		</div>
	</div>
</template>
<script>
export default {
	props: ['options', 'value'],
	methods: {
		update(option) {
			if(this.value.includes(option)){
				this.value.splice(this.value.indexOf(option), 1)
			} else {
				this.value.push(option)
			}
		},
	}
}
</script>
