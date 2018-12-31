<template>
	<div>
		<h2>Upload File</h2>
		<label for="">
			Select the doctype to import
			<input type="text">
		</label>
		<div class="upload-box">
			<input type="file" @change="load_file" accept=".csv, .xls" class="input-file"/>
			<p>
				Drag your file(s) here to begin<br> or click to browse
			</p>
		</div>
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
			const user_csv_file = ev.target.files[0];
			const reader = new FileReader();
			reader.readAsText(user_csv_file);
			reader.onload = (data) => {
				const csv = frappe.utils.csv_to_array(reader.result)
				const head = csv.shift()
				console.log(head, csv)
				let datatable = new DataTable(this.$refs.preview, {
					columns: head,
					data: csv
				})
			}
		}
	}
}
</script>
<style lang="less" scoped>
.upload-box {
	outline: 2px dashed grey; /* the dash box */
	color: dimgray;
	padding: 10px 10px;
	width: 50%;
	min-height: 400px; /* minimum height */
	position: relative;
	background-color: #f7f7f7;
	cursor: pointer;
}

.input-file {
	opacity: 0; /* invisible but it's there! */
	width: 100%;
	height: 200px;
	position: absolute;
	cursor: pointer;
}

.upload-box p {
	text-align: center;
	padding: 50px 0;
}
</style>

