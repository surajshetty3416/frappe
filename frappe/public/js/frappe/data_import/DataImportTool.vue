<template>
	<div>
		<label>
			Document Type:
			<input type="text" v-model="doctype" :disabled="doctype_verified" name="doctype" id="">
			<button :disabled="doctype_verified" @click="set_doctype">Submit</button>
		</label>
		<input type="file" @change="load_file" accept=".csv, .xls" class="input-file"/>
		<table v-if="docfields.length">
			<thead>
				<th>Doctype Field</th>
				<th>File Column</th>
			</thead>
			<tbody>
				<tr v-for="df in docfields" :key="df">
					<td>{{df}}</td>
					<td>
						<select>
							<option v-for="op in file_fields" :key="op">{{op}}</option>
						</select>
					</td>
				</tr>
			</tbody>
		</table>
	</div>
</template>
<script>
import DataTable from 'frappe-datatable';

export default {
	data() {
		return {
			file_fields: [],
			docfields: [],
			doctype_verified: false,
			doctype: null
		}
	},
	methods: {
		set_doctype() {
			this.doctype_verified = true
			frappe.model.with_doctype(this.doctype)
				.then(() => {
					this.docfields = this.get_fields(this.doctype);
				}).fail(() => {
					this.doctype_verified = false
				});
		},
		load_file(ev) {
			const user_csv_file = ev.target.files[0];
			const reader = new FileReader();
			reader.readAsText(user_csv_file);
			reader.onload = (data) => {
				const csv = frappe.utils.csv_to_array(reader.result)
				const head = csv.shift()
				this.file_fields = head;

				// console.log(head, csv)
				// let datatable = new DataTable(this.$refs.preview, {
					// 	columns: head,
				// 	data: csv
				// })
			}
		},
		filter_fields(df) {
			return frappe.model.is_value_type(df) && !df.hidden
		},
		get_fields(dt) {
			return frappe.meta.get_docfields(dt).filter(this.filter_fields).map(f => f.label)
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

// .input-file {
// 	opacity: 0; /* invisible but it's there! */
// 	width: 100%;
// 	height: 200px;
// 	position: absolute;
// 	cursor: pointer;
// }

.upload-box p {
	text-align: center;
	padding: 50px 0;
}
</style>

