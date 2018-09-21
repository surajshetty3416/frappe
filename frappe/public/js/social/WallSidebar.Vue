<template>
	<div>
		<!-- <div v-html='user_image'></div>
		<h2>
			{{socialData.name}}
		</h2> -->
		<div class='post-stats level flex-column'>
			<div class="stat" @click="handle()">
				<p class="text-muted font-weight-bold text-center">Posts</p>
				<p class="text-center text-large">{{ post_count }}</p>
			</div>
		</div>
	</div>
</template>
<script>
export default {
	data() {
		return {
			socialData: {},
			user_image: '',
			post_count: 0
		}
	},
	created() {
		frappe
			.xcall('frappe.core.doctype.social_profile.social_profile.get_social_data')
			.then(data => {
				this.socialData = data;
				this.user_image = frappe.avatar(data.name, 'avatar-xl')
			})

		frappe.db.count('Post', {
			filters: {
				'owner': frappe.session.user
			}
		}).then((post_count) => {
			this.post_count = post_count
		})

		frappe.realtime.on('new_post', (post) => {
			if (post.owner == frappe.session.user) {
				this.post_count += 1;
			}
		})
	},
	methods: {
		handle() {
			console.log('Stats');
		}
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
