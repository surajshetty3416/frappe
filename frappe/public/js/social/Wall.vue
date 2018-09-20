<template>
	<div class="container flex">
		<div v-for="(post, index) in posts" :key="index">
			<post :post="post"></post>
		</div>
	</div>
</template>
<script>
import Post from './Post.vue';
export default {
	components: {
		Post
	},
	data() {
		return {
			'posts': []
		}
	},
	created() {
		this.get_posts()
	},
	methods: {
		get_posts() {
			frappe.db.get_list('Post', {
				fields: ['name', 'content', 'owner', 'creation'],
			}).then((res) => {
				this.posts = res;
			});
		}
	}
};
</script>

<style lang='less' scoped>
.container{
	display: flex;
	flex-direction: column;
	padding: 10px;
	width: 500px;
	margin: 0;
}
</style>
