import frappe

from frappe.ai.permissions import FLOW_USER_ROLE, ensure_flow_role

FLOW_USER_ROLE_PROFILE = "Frappe Flow User"


def execute():
	"""Every logged-in user could use Flow before the role. Keep enabled System Managers on it."""
	ensure_flow_role()
	managers = frappe.get_all(
		"Has Role", filters={"role": "System Manager", "parenttype": "User"}, pluck="parent", distinct=True
	)
	accounts = set(
		frappe.get_all(
			"User", filters={"name": ("in", managers), "enabled": 1, "user_type": "System User"}, pluck="name"
		)
	)
	accounts.discard("Administrator")
	for name in sorted(accounts):
		_grant(frappe.get_doc("User", name))


def _grant(user):
	"""Profile-managed users receive an app-owned profile; shared profiles stay untouched."""
	if not user.role_profiles:
		user.add_roles(FLOW_USER_ROLE)
		return
	if FLOW_USER_ROLE_PROFILE in {row.role_profile for row in user.role_profiles}:
		return
	_ensure_flow_user_profile()
	user.append("role_profiles", {"role_profile": FLOW_USER_ROLE_PROFILE})
	user.save(ignore_permissions=True)


def _ensure_flow_user_profile() -> None:
	if frappe.db.exists("Role Profile", FLOW_USER_ROLE_PROFILE):
		roles = set(
			frappe.get_all(
				"Has Role",
				filters={"parent": FLOW_USER_ROLE_PROFILE, "parenttype": "Role Profile"},
				pluck="role",
			)
		)
		if roles != {FLOW_USER_ROLE}:
			frappe.throw(
				f"Role Profile {FLOW_USER_ROLE_PROFILE!r} already exists with unexpected roles; "
				"rename it before migrating Flow."
			)
		return
	frappe.get_doc(
		{
			"doctype": "Role Profile",
			"role_profile": FLOW_USER_ROLE_PROFILE,
			"roles": [{"role": FLOW_USER_ROLE}],
		}
	).insert(ignore_permissions=True)

