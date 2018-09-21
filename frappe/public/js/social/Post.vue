<template>
	<div class="post-card">
		<div class="pull-right text-muted" v-html="post_time"></div>
		<div class="user-avatar" v-html="user_avatar"></div>
		<div class="user-name">Suraj Shetty</div>
		<div class="content" v-html="post.content"></div>
	</div>
</template>
<script>
export default {
	props: ['post'],
	data() {
		return {
			user_avatar: frappe.avatar(this.post.owner, 'avatar-medium'),
			post_time: comment_when(this.post.creation)
		}
	}
}
</script>
<style lang="less">
.post-card {
	margin-bottom: 20px;
	padding: 10px 12px;
	max-width: 500px;
	max-height: 500px;
	min-height: 70px;
	overflow: hidden;
	.user-name{
		font-weight: 900;
	}
	.user-avatar {
		float: left;
		margin-right: 10px;
		.avatar {
			width: 48px;
			height: 48px;
		}
		.avatar-frame, .standard-image {
			border-radius: 50%;
		}
	}
	.content {
		margin-left: 58px;
		font-size: 14px;
		img, iframe {
			border-radius: 5px;
			border: none;
		}
	}

}
</style>
