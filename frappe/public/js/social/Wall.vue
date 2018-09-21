<template>
	<div class="container flex">
		<div class="new_posts_count" @click="load_new_posts()" v-if='new_posts_count'>{{ new_posts_count + ' new posts'}}</div>
		<div v-for="post in posts" :key="post.name">
			<post :post="post"></post>
		</div>
	</div>
</template>
<script>
import Post from './Post.vue';
import ActionCard from './ActionCard.vue';
export default {
	components: {
		Post
	},
	data() {
		return {
			'posts': [],
			'new_posts_count': 0
		}
	},
	created() {
		this.get_posts()
		frappe.realtime.on('new_post', (post_name) => {
			this.new_posts_count += 1;
		})
	},
	methods: {
		get_posts() {
			frappe.db.get_list('Post', {
				fields: ['name', 'content', 'owner', 'creation'],
			}).then((res) => {
				this.posts = res;
			});
		},
		load_new_posts() {
			this.get_posts() // TODO: make efficient
			this.new_posts_count = 0;
		}
	}
};
</script>

<style lang='less' scoped>
.container {
	display: flex;
	flex-direction: column;
	background: rgb(230, 236, 240);
	padding: 10px;
	width: 500px;
	font-size: 14px;
	margin: 0;
	.new_posts_count {
		height: 40px;
		cursor: pointer;
		background: rgb(205, 227, 241);
		text-align: center;
		padding: 10px;
	}
}
</style>
