# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

# Database Module
# --------------------

from __future__ import unicode_literals

def setup_database(force, verbose):
	import frappe
	if frappe.conf.db_type == 'postgres':
		import frappe.database.postgres.setup_db
		return frappe.database.postgres.setup_db.setup_database(force, verbose)
	else:
		import frappe.database.mariadb.setup_db
		return frappe.database.mariadb.setup_db.setup_database(force, verbose)

def drop_user_and_database(db_name, root_login=None, root_password=None):
	import frappe
	if frappe.conf.db_type == 'postgres':
		pass
	else:
		import frappe.database.mariadb.setup_db
		return frappe.database.mariadb.setup_db.drop_user_and_database(db_name, root_login, root_password)

def get_db(host=None, user=None, password=None):
	import frappe
	if frappe.conf.db_type == 'postgres':
		import frappe.database.postgres.database
		return frappe.database.postgres.database.PostgresDatabase(host, user, password)
	else:
		import frappe.database.mariadb.database
		return frappe.database.mariadb.database.MariaDBDatabase(host, user, password)
