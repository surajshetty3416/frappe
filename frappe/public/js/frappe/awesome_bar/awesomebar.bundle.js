import AwesomeBarUI from './AwesomeBar.vue';
frappe.provide("frappe.ui")

class AwesomeBar {
	constructor(parent) {
		this.awesomebar = new Vue({
			el: ".awe",
			render: (h) => h(AwesomeBarUI)
		}).$children[0];
	}
	show() {
		this.awesomebar.show();
	}
	hide() {
		this.awesomebar.hide();
	}
	toggle() {
		this.awesomebar.toggle();
	}
}

let div = $('<div class="awe">')
$('body').append(div)
frappe.ui.awesomebar = new AwesomeBar(div);