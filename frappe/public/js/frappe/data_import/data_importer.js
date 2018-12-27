import DataImportTool from './DataImportTool.vue';

frappe.DataImporter = class {
	constructor({ parent }) {
		this.$parent = $(parent);
		this.page = parent.page;
		this.setup_header();
		this.make_body();
	}
	make_body() {
		this.$social_container = this.$parent.find('.layout-main');
		frappe.require('/assets/js/frappe-vue.min.js', () => {
			new Vue({
				el: this.$social_container[0],
				render: h => h(DataImportTool)
			});
		});
	}
	setup_header() {
		this.page.set_title(__('Data Importer'));
	}
};