<template>
	<div class="user_permission_container padding">
		<input type="text" v-model="search">
		<table class="table table-bordered table-hover">
			<thead>
				<tr>
					<th>Allow</th>
					<th>For Value</th>
					<th>Applicable For</th>
					<th>&nbsp;</th>
				</tr>
			</thead>
			<tbody>
				<tr v-for="perm in filtered_user_permissions" :key="perm.name">
					<td>{{perm.allow}}</td>
					<td>{{perm.for_value}}</td>
					<td>
						<multi-check class="multicheck" :options="perm.linked_doctypes" :selected_items="perm.applicable_for"/>
					</td>
					<td>
						<button class="btn btn-sm" @click="save_user_permission(perm)">Save</button>
					</td>
				</tr>
			</tbody>
		</table>
	</div>
</template>
<script>
import MultiCheck from './components/MultiCheck.vue';
export default {
	props: ['user'],
	components: {
		MultiCheck,
	},
	data() {
		return {
			user_permissions: {},
			search: ''
		}
	},
	computed: {
		filtered_user_permissions() {
			if (this.search === '') {
				return this.user_permissions;
			} else {
				return Object.keys(this.user_permissions)
					.filter(key => key.toLowerCase().includes(this.search.toLowerCase()))
					.reduce((obj, key) => {
						obj[key] = this.user_permissions[key];
						return obj;
					}, {});
			}
		}
	},
	created() {
		frappe.xcall('frappe.core.doctype.user_permission.user_permission.get_consolidated_user_permission', {
			'user': this.user
		}).then(user_permissions => {
			this.user_permissions = user_permissions;
		});
	},
	methods: {
		save_user_permission(user_permission) {
			frappe.xcall('frappe.core.doctype.user_permission.user_permission.save_user_permission', {
				user_permission
			}).then()
		}
	}
}
</script>
<style lang="less">
.user_permission_container {
	font-size: 14px;
	.multicheck {
		max-height: 150px;
		max-width: 300px;
		overflow: scroll;
	}
}
</style>
