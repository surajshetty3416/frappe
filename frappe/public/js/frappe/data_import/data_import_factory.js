frappe.provide('frappe.views');
frappe.views.DataImportFactory = class DataImportFactory extends frappe.views.Factory {
	show() {
		if (frappe.pages.data_importer) {
			frappe.container.change_to('data_importer');
		} else {
			this.make('data_importer');
		}
	}

	make(page_name) {
		const assets = [
			'/assets/js/data_import.min.js'
		];

		frappe.require(assets, () => {
			new frappe.DataImporter({
				parent: this.make_page(true, page_name)
			});
		});
	}
};
