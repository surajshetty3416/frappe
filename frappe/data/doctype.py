def show_title_in_link(doc, method=None):
	if doc.custom and doc.title_field:
		doc.show_title_field_in_link = 1
