<template>
	<div>
		<img v-if='socialData.user_image' class="social-avatar" :src="socialData.user_image" alt="#">
		<div v-else class="standard-image">SS</div>
		<h2>
			{{socialData.name}}
		</h2>
	</div>
</template>
<script>
export default {
	data() {
		return {
			socialData: {}
		}
	},
	created() {
		frappe
			.xcall('frappe.core.doctype.social_profile.social_profile.get_social_data')
			.then(data => {
				this.socialData = data;
				console.log(data)
			})
	}
}
</script>
<style>
.social-avatar{
	width: 50%;
	height: auto;
	max-width: 250px;
	border-radius: 10px;
}
</style>
