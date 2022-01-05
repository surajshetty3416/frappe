<template>
	<div class="awesomebar">
		<input id="navbar-search" type="text" class="form-control" placeholder="Search or type a command (Ctrl + G)" aria-haspopup="true" autocomplete="off" aria-expanded="false" aria-owns="awesomplete_list_1" role="combobox">
	</div>
</template>
<script>
export default {
	name: "AwesomeBar",
	setup(props) {
		console.log('in');
	}
}
</script>
<style scoped>
.awesomebar {
	position: absolute;
	width: 300px;
	box-shadow: var(--shadow-lg);
	z-index: 15;
	top: 30%;
	left: 50%;
	transform: translate(-50%, -50%);
}
</style>