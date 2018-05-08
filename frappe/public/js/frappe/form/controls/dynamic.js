frappe.ui.form.ControlDynamicDate = frappe.ui.form.ControlInput.extend({
	html_element: "input",
	input_type: "text",
	make_input: function() {
		this.$input = $("<"+ this.html_element +">")
			.attr("type", this.input_type)
			.addClass("input-with-feedback form-control")
			.prependTo(this.input_area);
	},
	set_input: function(value){
		console.log('in', value)
	},
	get_input_value: function() {
		return this.$input ? this.$input.val() : undefined;
	},
	validate: function(value){
		debugger
		const allowed_values = [
			'Today',
			'Yesterday',
			'Tomorrow'
		]
		if (allowed_values.includes(value)) return value;
		else frappe.msgprint("Invalid input");
	}
});
