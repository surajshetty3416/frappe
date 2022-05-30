<template>
	<div>
		<div ref="user"></div>
		<div>
		<ul class="list-group mt-3">
			<li class="flex justify-between list-group-item" v-for="share in shared_with">
				<span>
					{{ share.user }}
				</span>
				<div class="btn-group">
					<button type="button" class="btn btn-xs btn-link dropdown-toggle" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
						{{ share.rights }}
					</button>
					<div class="dropdown-menu small">
						<button class="dropdown-item btn btn-link" v-for="option in rights_options">
							{{ option.label }}
						</button>
						<div class="dropdown-divider" v-if="actions"></div>
						<button class="dropdown-item btn btn-link" v-for="action in actions">
							{{ action.label }}
						</button>
					</div>
				</div>
			</li>
		</ul>
	</div>
	<h5 class="mt-5">
		<a> Get public Link -> </a>
	</h5>
	</div>
</template>
<script>
export default {
	props: ['frm'],
	mounted() {
		this.user = frappe.ui.form.make_control({
			parent: this.$refs.user,
			df: {
				label: __("Select User"),
				fieldname: "user",
				fieldtype: "Link",
				options: "User",
				change: () => {
					let user = this.user.get_value()
					if (user) {
						this.shared_with.push({
							user: user,
							can_share: true,
							rights: "Can Read"
						})
						this.user.set_value('')
					}
				}
			},
			render_input: true
		});
	},
	data() {
		return {
			shared_with: [{
				user: "suraj@erpnext.com",
				can_share: true,
				rights: "Can Read"
			}, {
				user: "faris@erpnext.com",
				can_share: true,
				rights: "Can Write"
			}],
			rights_options: [{
				label: "Can Read",
				value: "can_read"
			}, {
				label: "Can Write",
				value: "can_write"
			}, {
				label: "Can Share",
				value: "can_share"
			}],
			actions: [{
				label: "Delete",
				value: "delete"
			}]
		}
	}

}
</script>