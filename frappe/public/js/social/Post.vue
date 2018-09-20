<template>
	<div class="post-card" >
		<img src="/files/IMG-20170117-WA0011.jpg" class="user-avatar">
		<div class="user-name">Suraj Shetty</div>
		<div class="text-muted pull-right"> 5h</div>
		<div class="content" v-html="post.content"></div>
	</div>
</template>
<script>
export default {
	props: ['post']
}
</script>
<style lang="less">
.post-card {
	margin-bottom: 20px;
	border-radius: 5px;
	padding: 10px 12px;
	max-width: 500px;
	max-height: 500px;
	min-height: 70px;
	background: rgb(230, 236, 240);
	.user-name{
		font-weight: 900;
	}
	.user-avatar {
		float: left;
		width: 48px;
		height: 48px;
		border-radius: 50%;
		margin-right: 10px
	}
	.content{
		margin-left: 58px;
		font-size: 14px;
		img{
			border-radius: 5px;
		}
	}

}
</style>
