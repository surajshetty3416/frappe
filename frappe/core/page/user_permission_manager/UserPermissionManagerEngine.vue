<template>
	<div class="user-permission-container padding">
		<input type="text" v-model="search">
		<table class="table table-bordered table-hover">
			<thead>
				<tr>
					<th>Allow</th>
					<th>For Value</th>
					<th class="applicable-for-column">Applicable For</th>
					<th>&nbsp;</th>
				</tr>
			</thead>
			<tbody>
				<tr v-for="(perm, key) in filtered_user_permissions" :key="key">
					<td>{{perm.allow}}</td>
					<td>{{perm.for_value}}</td>
					<td>
						<multi-check class="multicheck"
							v-model="perm.applicable_for"
							:options="perm.linked_doctypes"
						/>
					</td>
					<td>
						<button class="btn btn-sm" @click="save_user_permission(perm)">Save</button>
						<button class="btn btn-sm" @click="delete_user_permission(key)">Delete</button>
					</td>
				</tr>
			</tbody>
		</table>
		<button class="btn btn-primary" @click="open_modal">Add New User Permission</button>
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
			frappe.dom.freeze();
			frappe.xcall('frappe.core.doctype.user_permission.user_permission.save_user_permission', {
				user_permission
			}).then(() => {
				frappe.dom.unfreeze();
				frappe.show_alert('Saved!')
			})
		},
		delete_user_permission(key) {
			frappe.dom.freeze();
			frappe.xcall('frappe.core.doctype.user_permission.user_permission.delete_user_permission', {
				'user_permission': this.user_permissions[key]
			}).then(() => {
				this.$delete(this.user_permissions, key)
				frappe.dom.unfreeze();
				frappe.show_alert('Deleted!')
			})
		},
		open_modal() {
			frappe.user_permission_dialog.show()
		}
	}
}
</script>
<style lang="less">
.user-permission-container {
	font-size: 14px;
	.applicable-for-column {
		width: 50%;
	}
	.multicheck {
		max-height: 150px;
		overflow: scroll;
	}
}
</style>
