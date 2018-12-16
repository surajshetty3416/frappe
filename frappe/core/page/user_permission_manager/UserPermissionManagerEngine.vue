<template>
	<div class="user_permission_container padding">
		<table class="table table-bordered table-hover">
			<thead>
				<tr>
					<th>Allow</th>
					<th>For Value</th>
					<th>Applicable For</th>
				</tr>
			</thead>
			<tbody>
				<tr v-for="perm in user_permissions" :key="perm.name">
					<td>{{perm.allow}}</td>
					<td>{{perm.for_value}}</td>
					<td>
						<multi-check class="multicheck" :options="perm.linked_doctypes" :selected_items="perm.applicable_for"/>
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
			user_permissions: [],
		}
	},
	created() {
		frappe.xcall('frappe.core.doctype.user_permission.user_permission.get_consolidated_user_permission', {
			'user': this.user
		}).then(user_permissions => {
			this.user_permissions = user_permissions;
		});
	}
}
</script>
<style lang="less">
.user_permission_container {
	font-size: 14px;
	.multicheck {
		max-height: 150px;
		overflow: scroll;
	}
}
</style>
