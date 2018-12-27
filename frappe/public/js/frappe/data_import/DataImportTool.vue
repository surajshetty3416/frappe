<template>
	<div>
		<input type="file" @change="load_file" accept=".csv, .xls" />
		<div ref="preview"></div>
	</div>
</template>
<script>
import DataTable from 'frappe-datatable';

export default {
	data() {
		return {}
	},
	methods: {
		load_file(ev) {
			console.log(ev.target.files[0]);
			const user_csv_file = ev.target.files[0];
			const reader = new FileReader();
			reader.readAsText(user_csv_file);
			reader.onload = (data) => {
				const csv = reader.result.split('\n').map(d => d.split(','))
				console.log(csv);

				let datatable = new DataTable(this.$refs.preview, {
					columns: csv.shift(),
					data: csv
				})
			}
		}
	}
}
</script>
