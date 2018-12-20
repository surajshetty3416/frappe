# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, json
from frappe.model.document import Document
from frappe.permissions import (get_valid_perms, update_permission_property)
from frappe import _
from frappe.core.utils import find
from frappe.desk.form.linked_with import get_linked_doctypes

class UserPermission(Document):
	def validate(self):
		duplicate_exists = frappe.db.get_all(self.doctype, filters={
			'allow': self.allow,
			'for_value': self.for_value,
			'user': self.user,
			'applicable_for': self.applicable_for,
			'apply_to_all_doctypes': self.apply_to_all_doctypes,
			'name': ['!=', self.name]
		}, limit=1)
		if duplicate_exists:
			frappe.throw(_("User permission already exists"), frappe.DuplicateEntryError)

	def on_update(self):
		frappe.cache().delete_value('user_permissions')
		frappe.publish_realtime('update_user_permissions')

	def on_trash(self): # pylint: disable=no-self-use
		frappe.cache().delete_value('user_permissions')
		frappe.publish_realtime('update_user_permissions')

@frappe.whitelist()
def get_user_permissions(user=None):
	'''Get all users permissions for the user as a dict of doctype'''
	# if this is called from client-side,
	# user can access only his/her user permissions
	if frappe.request and frappe.local.form_dict.cmd == 'get_user_permissions':
		user = frappe.session.user

	if not user:
		user = frappe.session.user

	cached_user_permissions = frappe.cache().hget("user_permissions", user)

	if cached_user_permissions is not None:
		return cached_user_permissions

	out = {}

	def add_doc_to_perm(perm, doc_name):
		# group rules for each type
		# for example if allow is "Customer", then build all allowed customers
		# in a list
		if not out.get(perm.allow):
			out[perm.allow] = []

		out[perm.allow].append({
			'doc': doc_name,
			'applicable_for': perm.get('applicable_for')
		})

	try:
		for perm in frappe.get_all('User Permission',
			fields=['allow', 'for_value', 'applicable_for'],
			filters=dict(user=user)):

			meta = frappe.get_meta(perm.allow)
			add_doc_to_perm(perm, perm.for_value)

			if meta.is_nested_set():
				decendants = frappe.db.get_descendants(perm.allow, perm.for_value)
				for doc in decendants:
					add_doc_to_perm(perm, doc)

		frappe.cache().hset("user_permissions", user, out)

	except frappe.SQLError as e:
		if e.args[0]==1146:
			# called from patch
			pass

	return out

def user_permission_exists(user, allow, for_value, applicable_for=None):
	'''Checks if similar user permission already exists'''
	user_permissions = get_user_permissions(user).get(allow, [])
	if not user_permissions: return None
	has_same_user_permission = find(user_permissions, lambda perm:perm["doc"] == for_value and perm.get('applicable_for') == applicable_for)

	return has_same_user_permission

def get_applicable_for_doctype_list(doctype, txt, searchfield, start, page_len, filters):
	linked_doctypes = get_linked_doctypes(doctype, True).keys()
	linked_doctypes += [doctype]
	if txt:
		linked_doctypes = [d for d in linked_doctypes if txt in d.lower()]

	linked_doctypes.sort()

	return_list = []
	for doctype in linked_doctypes[start:page_len]:
		return_list.append([doctype])

	return return_list

@frappe.whitelist()
def get_consolidated_user_permission(user):
	user_permissions = frappe.get_all('User Permission',
		filters={'user': user},
		fields=['allow', 'user', 'for_value', 'applicable_for', 'apply_to_all_doctypes'])

	consolidated_user_permissions = {}

	for perm in user_permissions:
		key = perm.allow + perm.for_value
		if consolidated_user_permissions.get(key) == None:
			consolidated_user_permissions[key] = {
				'user': perm.user,
				'allow': perm.allow,
				'for_value': perm.for_value,
				'applicable_for': [perm.applicable_for] if perm.applicable_for else [],
				'linked_doctypes': get_all_linked_with_doctypes(perm.allow)
			}
		else:
			consolidated_user_permissions[key].get('applicable_for').append(perm.applicable_for)

	return consolidated_user_permissions

@frappe.whitelist()
def save_user_permission(user_permission):
	user_permission = json.loads(user_permission)
	current_doctypes = frappe.db.get_values('User Permission', filters={
		'allow': user_permission['allow'],
		'for_value': user_permission['for_value'],
		'user': user_permission['user']
	}, fieldname='applicable_for', as_dict=1)

	current_doctypes = [d.applicable_for for d in current_doctypes]

	if set(current_doctypes) == set(user_permission['applicable_for']):
		return

	new_applicable_for = list(set(user_permission['applicable_for']) - set(current_doctypes))

	applicable_for_to_delete = list(set(current_doctypes) - set(user_permission['applicable_for']))

	applicable_for_all_doctype = set(user_permission['applicable_for']) == get_all_linked_with_doctypes(user_permission['allow'])

	if applicable_for_all_doctype:
		frappe.get_doc({
			'doctype': 'User Permission',
			'allow': user_permission['allow'],
			'for_value': user_permission['for_value'],
			'user': user_permission['user'],
			'apply_to_all_doctypes': 1
		}).insert()
		applicable_for_to_delete = current_doctypes
	else:
		for doctype in new_applicable_for:
			frappe.get_doc({
				'doctype': 'User Permission',
				'allow': user_permission['allow'],
				'for_value': user_permission['for_value'],
				'user': user_permission['user'],
				'applicable_for': doctype,
				'apply_to_all_doctypes': 0
			}).insert()

	for doctype in applicable_for_to_delete:
		frappe.db.sql('''DELETE FROM `tabUser Permission` WHERE
			`user`=%(user)s AND
			`allow`=%(allow)s AND
			`for_value`=%(for_value)s AND
			`applicable_for`=%(applicable_for)s''', dict(
				user=user_permission['user'],
				allow=user_permission['allow'],
				for_value=user_permission['for_value'],
				applicable_for=doctype
			),
		)

@frappe.whitelist()
def delete_user_permission(user_permission):
	user_permission = json.loads(user_permission)
	frappe.db.sql('''DELETE FROM `tabUser Permission` WHERE
			user=%(user)s AND
			allow=%(allow)s AND
			for_value=%(for_value)s''', dict(
				user=user_permission['user'],
				allow=user_permission['allow'],
				for_value=user_permission['for_value'],
			)
		)

def get_permitted_documents(doctype):
	return [d.get('doc') for d in get_user_permissions().get(doctype, []) \
		if d.get('doc')]

def get_all_linked_with_doctypes(doctype):
	return set(get_linked_doctypes(doctype, True).keys() + [doctype])
