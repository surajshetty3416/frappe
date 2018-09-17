<template>
	<div class="container flex">
		<div class="social-card" v-for="card in cards" :key="card.id">
			<div class="card-body">
				<span class="bold">{{card.title}}</span>
				<span>{{card.message}}</span>
			</div>
			<div class="card-foot">
				<span>This is a footer message</span>
			</div>
		</div>
	</div>
</template>
<script>
export default {
	data() {
		return {
			'cards': [{
				id: 1,
				title: 'Suraj Shetty',
				message: 'Hey there! This is Social Message 🤘',
			},{
				id: 2,
				title: 'Suraj Shetty',
				message: 'Hey there! This is Social Message 🤘',
			},{
				id: 3,
				title: 'Suraj Shetty',
				message: 'Hey there! This is Social Message 🤘',
			},{
				id: 4,
				title: 'Suraj Shetty',
				message: 'Hey there! This is Social Message 🤘',
			}]
		}
	}
};
</script>

<style lang='less' scoped>
.container{
	display: flex;
	flex-direction: column;
	padding: 10px;
}
.social-card {
	margin-bottom: 20px;
	width: 300px;
	height: auto;
	display: flex;
	flex-direction: column;
	overflow: hidden;
	justify-content: space-between;
	border-radius: 5px;
	.card-body{
		padding: 10px;
	}
	.card-foot{
		padding: 5px;
		background: lightgrey;
	}
}
.social-card:hover{
	border: 1px solid lightgrey;
}
</style>
