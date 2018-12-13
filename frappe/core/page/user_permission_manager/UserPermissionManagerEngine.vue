<template>
	<div class="container padding">
		<table class="table table-bordered">
			<thead>
				<tr>
					<th>Allow</th>
					<th>For Value</th>
					<th>Applicable For</th>
					<th>&nbsp;</th>
				</tr>
			</thead>
			<tbody>
				<tr v-for="perm in user_permissions" :key="perm.name">
					<td>{{perm.allow}}</td>
					<td>{{perm.for_value}}</td>
					 <td><multi-check :options="['Test', 'Test2']"></multi-check></td>
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
			user_permissions: [{
				'name': 'asdf',
				'allow': 'User',
				'for_value': 'suraj@erpnext.com'
			}]
		}
	},
	methods: {

	}
}
</script>

<style lang="less" scoped>
.container {

}
</style>
