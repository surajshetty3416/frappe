<template>
	<div>
		<div v-html='user_image'></div>
		<h2>
			{{socialData.name}}
		</h2>
	</div>
</template>
<script>
export default {
	data() {
		return {
			socialData: {},
			user_image: ''
		}
	},
	created() {
		frappe
			.xcall('frappe.core.doctype.social_profile.social_profile.get_social_data')
			.then(data => {
				this.socialData = data;
				this.user_image = frappe.avatar(data.name, 'avatar-xl')
			})
	}
}
</script>
<style>
.social-avatar {
	width: 50%;
	height: auto;
	max-width: 250px;
	border-radius: 10px;
}
</style>
