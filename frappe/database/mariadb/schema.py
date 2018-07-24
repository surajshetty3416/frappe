from __future__ import unicode_literals

import re
import os
import frappe
from frappe import _
from frappe.utils import cstr, cint, flt

class MariaDBTable():
	def __init__(self, doctype, meta=None):
		self.doctype = doctype
		self.table_name = 'tab{}'.format(doctype)
		self.meta = meta or frappe.get_meta(doctype)
		self.columns = {}
		self.current_columns = {}

		# lists for change
		self.add_column = []
		self.change_type = []
		self.add_index = []
		self.drop_index = []
		self.set_default = []

		# load
		self.get_columns_from_docfields()

	def sync(self):
		if self.is_new():
			self.create()
		else:
			self.alter()

	def create(self):
		add_text = ''

		# columns
		column_defs = self.get_column_definitions()
		if column_defs: add_text += ',\n'.join(column_defs) + ',\n'

		# index
		index_defs = self.get_index_definitions()
		if index_defs: add_text += ',\n'.join(index_defs) + ',\n'

		# create table
		frappe.db.sql("""create table `%s` (
			name varchar({varchar_len}) not null primary key,
			creation datetime(6),
			modified datetime(6),
			modified_by varchar({varchar_len}),
			owner varchar({varchar_len}),
			docstatus int(1) not null default '0',
			parent varchar({varchar_len}),
			parentfield varchar({varchar_len}),
			parenttype varchar({varchar_len}),
			idx int(8) not null default '0',
			%sindex parent(parent),
			index modified(modified))
			ENGINE={engine}
			ROW_FORMAT=COMPRESSED
			CHARACTER SET=utf8mb4
			COLLATE=utf8mb4_unicode_ci""".format(varchar_len=frappe.db.VARCHAR_LEN,
				engine=self.meta.get("engine") or 'InnoDB') % (self.table_name, add_text))

	def get_column_definitions(self):
		column_list = [] + frappe.db.DEFAULT_COLUMNS
		ret = []
		for k in list(self.columns):
			if k not in column_list:
				d = self.columns[k].get_definition()
				if d:
					ret.append('`'+ k + '` ' + d)
					column_list.append(k)
		return ret

	def get_index_definitions(self):
		ret = []
		for key, col in self.columns.items():
			if col.set_index and not col.unique and col.fieldtype in frappe.db.type_map and \
					frappe.db.type_map.get(col.fieldtype)[0] not in ('text', 'longtext'):
				ret.append('index `' + key + '`(`' + key + '`)')
		return ret

	def get_columns_from_docfields(self):
		"""
			get columns from docfields and custom fields
		"""
		fl = frappe.db.sql("SELECT * FROM tabDocField WHERE parent = %s", self.doctype, as_dict = 1)
		lengths = {}
		precisions = {}
		uniques = {}

		# optional fields like _comments
		if not self.meta.istable:
			for fieldname in frappe.db.OPTIONAL_COLUMNS:
				fl.append({
					"fieldname": fieldname,
					"fieldtype": "Text"
				})

			# add _seen column if track_seen
			if getattr(self.meta, 'track_seen', False):
				fl.append({
					'fieldname': '_seen',
					'fieldtype': 'Text'
				})

		if not frappe.flags.in_install_db and (frappe.flags.in_install != "frappe" or frappe.flags.ignore_in_install):
			custom_fl = frappe.db.sql("""\
				SELECT * FROM `tabCustom Field`
				WHERE dt = %s AND docstatus < 2""", (self.doctype,), as_dict=1)
			if custom_fl: fl += custom_fl

			# apply length, precision and unique from property setters
			for ps in frappe.get_all("Property Setter", fields=["field_name", "property", "value"],
				filters={
					"doc_type": self.doctype,
					"doctype_or_field": "DocField",
					"property": ["in", ["precision", "length", "unique"]]
				}):

				if ps.property=="length":
					lengths[ps.field_name] = cint(ps.value)

				elif ps.property=="precision":
					precisions[ps.field_name] = cint(ps.value)

				elif ps.property=="unique":
					uniques[ps.field_name] = cint(ps.value)

		for f in fl:
			self.columns[f['fieldname']] = DbColumn(self, f['fieldname'],
				f['fieldtype'], lengths.get(f["fieldname"]) or f.get('length'), f.get('default'), f.get('search_index'),
				f.get('options'), uniques.get(f["fieldname"], f.get('unique')), precisions.get(f['fieldname']) or f.get('precision'))

	def validate(self):
		"""Check if change in varchar length isn't truncating the columns"""
		if self.is_new():
			return

		self.setup_table_colums()

		columns = [frappe._dict({"fieldname": f, "fieldtype": "Data"}) for f in frappe.db.STANDARD_VARCHAR_COLUMNS]
		columns += self.columns.values()

		for col in columns:
			if len(col.fieldname) >= 64:
				frappe.throw(_("Fieldname is limited to 64 characters ({0})")
					.format(frappe.bold(col.fieldname)))

			if 'varchar' in frappe.db.type_map.get(col.fieldtype, ()):

				# validate length range
				new_length = cint(col.length) or cint(frappe.db.VARCHAR_LEN)
				if not (1 <= new_length <= 1000):
					frappe.throw(_("Length of {0} should be between 1 and 1000").format(col.fieldname))

				current_col = self.current_columns.get(col.fieldname, {})
				if not current_col:
					continue
				current_type = self.current_columns[col.fieldname]["type"]
				current_length = re.findall('varchar\(([\d]+)\)', current_type)
				if not current_length:
					# case when the field is no longer a varchar
					continue
				current_length = current_length[0]
				if cint(current_length) != cint(new_length):
					try:
						# check for truncation
						max_length = frappe.db.sql("""select max(char_length(`{fieldname}`)) from `tab{doctype}`"""\
							.format(fieldname=col.fieldname, doctype=self.doctype))

					except frappe.db.InternalError as e:
						if frappe.db.is_missing_column(e):
							# Unknown column 'column_name' in 'field list'
							continue

						else:
							raise

					if max_length and max_length[0][0] and max_length[0][0] > new_length:
						if col.fieldname in self.columns:
							self.columns[col.fieldname].length = current_length

						frappe.msgprint(_("Reverting length to {0} for '{1}' in '{2}'; Setting the length as {3} will cause truncation of data.")\
							.format(current_length, col.fieldname, self.doctype, new_length))

	def is_new(self):
		return self.table_name not in frappe.db.get_tables()

	def setup_table_colums(self):
		for c in frappe.db.sql("desc `%s`" % self.table_name):
			self.current_columns[c[0].lower()] = {
				'name': c[0],
				'type': c[1],
				'index': c[3]=="MUL",
				'default': c[4],
				'unique': c[3]=="UNI"
			}

	def alter(self):
		for col in self.columns.values():
			col.build_for_alter_table(self.current_columns.get(col.fieldname.lower(), None))

		query = []

		for col in self.add_column:
			query.append("add column `{}` {}".format(col.fieldname, col.get_definition()))

		for col in self.change_type:
			current_def = self.current_columns.get(col.fieldname.lower(), None)
			query.append("change `{}` `{}` {}".format(current_def["name"], col.fieldname, col.get_definition()))

		for col in self.add_index:
			# if index key not exists
			if not frappe.db.sql("show index from `%s` where key_name = %s" %
					(self.table_name, '%s'), col.fieldname):
				query.append("add index `{}`(`{}`)".format(col.fieldname, col.fieldname))

		for col in self.drop_index:
			if col.fieldname != 'name': # primary key
				# if index key exists
				if frappe.db.sql("""show index from `{0}`
					where key_name=%s
					and Non_unique=%s""".format(self.table_name), (col.fieldname, col.unique)):
					query.append("drop index `{}`".format(col.fieldname))

		for col in self.set_default:
			if col.fieldname=="name":
				continue

			if col.fieldtype in ("Check", "Int"):
				col_default = cint(col.default)

			elif col.fieldtype in ("Currency", "Float", "Percent"):
				col_default = flt(col.default)

			elif not col.default:
				col_default = "null"

			else:
				col_default = '"{}"'.format(col.default.replace('"', '\\"'))

			query.append('alter column `{}` set default {}'.format(col.fieldname, col_default))

		if query:
			try:
				frappe.db.sql("alter table `{}` {}".format(self.table_name, ", ".join(query)))
			except Exception as e:
				# sanitize
				if e.args[0]==1060:
					frappe.throw(str(e))
				elif e.args[0]==1062:
					fieldname = str(e).split("'")[-2]
					frappe.throw(_("{0} field cannot be set as unique in {1}, as there are non-unique existing values".format(
						fieldname, self.table_name)))
				else:
					raise e

	def get_foreign_keys(self):
		fk_list = []
		txt = frappe.db.sql("show create table `%s`" % self.table_name)[0][1]
		for line in txt.split('\n'):
			if line.strip().startswith('CONSTRAINT') and line.find('FOREIGN')!=-1:
				try:
					fk_list.append((line.split('`')[3], line.split('`')[1]))
				except IndexError:
					pass

		return fk_list

def validate_column_name(n):
	special_characters = re.findall(r"[\W]", n, re.UNICODE)
	if special_characters:
		special_characters = ", ".join('"{0}"'.format(c) for c in special_characters)
		frappe.throw(_("Fieldname {0} cannot have special characters like {1}").format(
			frappe.bold(cstr(n)), special_characters), frappe.db.InvalidColumnName)
	return n

def validate_column_length(fieldname):
	""" In MySQL maximum column length is 64 characters,
		ref: https://dev.mysql.com/doc/refman/5.5/en/identifiers.html"""

	if len(fieldname) > 64:
		frappe.throw(_("Fieldname is limited to 64 characters ({0})").format(fieldname))

def get_definition(fieldtype, precision=None, length=None):
	d = frappe.db.type_map.get(fieldtype)

	# convert int to long int if the length of the int is greater than 11
	if fieldtype == "Int" and length and length>11:
		d = frappe.db.type_map.get("Long Int")

	if not d:
		return

	coltype = d[0]
	size = None
	if d[1]:
		size = d[1]

	if size:
		if fieldtype in ["Float", "Currency", "Percent"] and cint(precision) > 6:
			size = '21,9'

		if coltype == "varchar" and length:
			size = length

	if size is not None:
		coltype = "{coltype}({size})".format(coltype=coltype, size=size)

	return coltype

def add_column(doctype, column_name, fieldtype, precision=None):
	if column_name in frappe.db.get_table_columns(doctype):
		# already exists
		return

	frappe.db.commit()
	frappe.db.sql("alter table `tab%s` add column %s %s" % (doctype,
		column_name, get_definition(fieldtype, precision)))


class DbColumn:
	def __init__(self, table, fieldname, fieldtype, length, default,
		set_index, options, unique, precision):
		self.table = table
		self.fieldname = fieldname
		self.fieldtype = fieldtype
		self.length = length
		self.set_index = set_index
		self.default = default
		self.options = options
		self.unique = unique
		self.precision = precision

	def get_definition(self, with_default=1):
		column_def = get_definition(self.fieldtype, precision=self.precision, length=self.length)

		if not column_def:
			return column_def

		if self.fieldtype in ("Check", "Int"):
			default_value = cint(self.default) or 0
			column_def += ' not null default {0}'.format(default_value)

		elif self.fieldtype in ("Currency", "Float", "Percent"):
			default_value = flt(self.default) or 0
			column_def += ' not null default {0}'.format(default_value)

		elif self.default and (self.default not in frappe.db.DEFAULT_SHORTCUTS) \
			and not self.default.startswith(":") and column_def not in ('text', 'longtext'):
			column_def += ' default "' + self.default.replace('"', '\"') + '"'

		if self.unique and (column_def not in ('text', 'longtext')):
			column_def += ' unique'

		return column_def

	def build_for_alter_table(self, current_def):
		column_def = get_definition(self.fieldtype, self.precision, self.length)

		# no columns
		if not column_def:
			return

		# to add?
		if not current_def:
			self.fieldname = validate_column_name(self.fieldname)
			self.table.add_column.append(self)
			return

		# type
		if (current_def['type'] != column_def) or\
			self.fieldname != current_def['name'] or\
			((self.unique and not current_def['unique']) and column_def not in ('text', 'longtext')):
			self.table.change_type.append(self)

		else:
			# default
			if (self.default_changed(current_def) \
				and (self.default not in frappe.db.DEFAULT_SHORTCUTS) \
				and not cstr(self.default).startswith(":") \
				and not (column_def in ['text','longtext'])):
				self.table.set_default.append(self)

		# index should be applied or dropped irrespective of type change
		if ( (current_def['index'] and not self.set_index and not self.unique)
			or (current_def['unique'] and not self.unique) ):
			# to drop unique you have to drop index
			self.table.drop_index.append(self)

		elif (not current_def['index'] and self.set_index) and not (column_def in ('text', 'longtext')):
			self.table.add_index.append(self)

	def default_changed(self, current_def):
		if "decimal" in current_def['type']:
			return self.default_changed_for_decimal(current_def)
		else:
			return current_def['default'] != self.default

	def default_changed_for_decimal(self, current_def):
		try:
			if current_def['default'] in ("", None) and self.default in ("", None):
				# both none, empty
				return False

			elif current_def['default'] in ("", None):
				try:
					# check if new default value is valid
					float(self.default)
					return True
				except ValueError:
					return False

			elif self.default in ("", None):
				# new default value is empty
				return True

			else:
				# NOTE float() raise ValueError when "" or None is passed
				return float(current_def['default'])!=float(self.default)
		except TypeError:
			return True
