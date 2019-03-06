# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class ActivityCounter(Document):
	pass

def update_activity_counter(user, activity_counter_type):
	if user == 'admin@example.com':
		user = 'Administrator'
	count = frappe.db.get_all('Activity Counter', filters={
		'user': user,
		'type': activity_counter_type
	}, fields=['name', 'count'], limit=1)

	if count:
		activity_counter = frappe.get_doc('Activity Counter', count[0].name)
		activity_counter.count += 1
		activity_counter.save()

	else:
		frappe.get_doc({
			'doctype': 'Activity Counter',
			'user': user,
			'type': activity_counter_type,
			'count': 1
		}).insert()