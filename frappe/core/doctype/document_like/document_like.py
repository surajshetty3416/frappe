# Copyright (c) 2022, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class DocumentLike(Document):
	def after_insert(self):
		frappe.publish_realtime(f'document-like-{self.reference_doctype}-{self.reference_docname}',
			{'unlike': False, 'owner': self.owner})

	def on_trash(self):
		frappe.publish_realtime(f'document-like-{self.reference_doctype}-{self.reference_docname}',
			{'unlike': True, 'owner': self.owner})

@frappe.whitelist()
def get_likes(reference_doctype, reference_docname):
	likes = frappe.get_all('Document Like', filters={
		"reference_doctype": reference_doctype,
		"reference_docname": reference_docname
	}, fields=['owner'], pluck='owner')
	print(likes, reference_doctype, reference_docname)
	return likes

@frappe.whitelist()
def toggle_like(reference_doctype, reference_docname):
	if like_exists := frappe.db.exists(
		"Document Like",
		{
			"reference_docname": reference_docname,
			"reference_doctype": reference_doctype,
			"owner": frappe.session.user
		},
	):
		print(like_exists)
		frappe.delete_doc("Document Like", like_exists)
	else:
		doc = frappe.get_doc({
			"doctype": "Document Like",
			"reference_docname": reference_docname,
			"reference_doctype": reference_doctype
		})
		doc.insert(ignore_permissions=True)