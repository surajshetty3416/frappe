# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies and Contributors
# See license.txt
from __future__ import unicode_literals

#import frappe
import unittest

class TestUserPermission(unittest.TestCase):
	def test_save_user_permission(self):
		from .user_permission import save_user_permission


		# case 1 applicable for all should create one record and delete others if exist
		# case 2 if only one is unchecked, applicable for all record should be deleted and other should be created
		# case 3
