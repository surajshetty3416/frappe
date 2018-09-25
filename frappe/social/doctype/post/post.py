# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class Post(Document):
	def after_insert(self):
		frappe.publish_realtime('new_post', self, after_commit=True)

@frappe.whitelist()
def add_comment(post_name, comment):
	post = frappe.get_doc('Post', post_name)
	post.append('comments', {
		'content': comment
	})
	post.save()
	frappe.publish_realtime('new_post_comment', post_name, after_commit=True)