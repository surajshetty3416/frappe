<template>
	<div class="awesomebar_v2">
		<div class="backdrop"></div>
		<search-bar></search-bar>
	</div>
</template>
<script>
import InputBar from "./components/InputBar.vue";
export default {
	name: "AwesomeBar",
	components: {
		InputBar
	},
	setup(props) {
		console.log('in');
	},
	methods: {
		show() {
			$(".awesomebar_v2").show();
		},
		hide() {
			$(".awesomebar_v2").hide();
		},
		toggle() {
			$(".awesomebar_v2").toggle();
		}
	},
}
</script>
<style scoped>
.awesomebar_v2 {
	display: none;
	position: absolute;
	width: min(500px, 80vw);
	box-shadow: var(--shadow-lg);
	z-index: 15;
	top: 30%;
	left: 50%;
	height: 50px;
	transform: translate(-50%, -50%);
	border: 1px solid var(--dark-border-color);
	border-radius: var(--border-radius);
}
</style>


// Awesome bar
// 	- Input
// 		- Command
// 			- Sub Command
// 	- Options
// 		- Categories
// 	- Action
// 	- Alias
// 	- Modes
// 		- Command
// 		- Navigation
// 		- Search
// -----------------------------

// Form
// 	- Custom actions
// 	- Share
// 	- Assign
// 	- Menu Options

// List view
// 	- Change view
// 	-