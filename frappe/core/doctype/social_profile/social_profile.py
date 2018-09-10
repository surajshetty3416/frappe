# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import cint

class SocialProfile(Document):
	pass

def update_user_energy_point(point, user=None):
	point = cint(point)
	if not point: return
	# TODO: find alternative
	if user == 'admin@erpnext.com': user = 'Administrator'
	if not user: user = frappe.session.user
	previous_point = frappe.db.get_value('Social Profile', user, 'energy_point')
	new_point = previous_point + point
	frappe.db.set_value('Social Profile', user, 'energy_point', new_point)

	print('================= {} gained {} points ==================='.format(user, point))