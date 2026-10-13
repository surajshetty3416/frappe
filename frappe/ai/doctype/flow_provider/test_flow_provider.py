# Copyright (c) 2026, Frappe Technologies and Contributors
# See license.txt

from typing import Any

import frappe
from frappe.ai.lib.model import model_config
from frappe.tests import IntegrationTestCase


def _provider(**overrides: Any) -> dict:
	doc = {"doctype": "Flow Provider", "provider": "openrouter", "api_key": "sk-provider", "enabled": 1}
	doc.update(overrides)
	return doc


def _model(**overrides: Any) -> dict:
	doc = {
		"doctype": "Flow Model",
		"title": "Test Provider Model",
		"model_id": "openrouter/test/model",
		"enabled": 1,
	}
	doc.update(overrides)
	return doc


class TestFlowProviderValidation(IntegrationTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_inserts_with_known_provider(self):
		doc = frappe.get_doc(_provider()).insert()
		self.assertEqual(doc.name, "openrouter")

	def test_provider_name_normalized_lowercase(self):
		doc = frappe.get_doc(_provider(provider="OpenRouter")).insert()
		self.assertEqual(doc.provider, "openrouter")

	def test_unknown_provider_rejected(self):
		doc = frappe.get_doc(_provider(provider="not-a-real-provider"))
		with self.assertRaisesRegex(frappe.ValidationError, "Unknown provider"):
			doc.insert()

	def test_invalid_base_url_rejected(self):
		doc = frappe.get_doc(_provider(base_url="not-a-url"))
		with self.assertRaisesRegex(frappe.ValidationError, "Base URL"):
			doc.insert()


class TestProviderCredentialResolution(IntegrationTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_model_resolves_key_from_provider(self):
		frappe.get_doc(_provider(api_key="sk-from-provider")).insert()
		m = frappe.get_doc(_model()).insert()
		self.assertEqual(model_config(m.name)["api_key"], "sk-from-provider")

	def test_model_own_key_overrides_provider(self):
		frappe.get_doc(_provider(api_key="sk-from-provider")).insert()
		m = frappe.get_doc(_model(api_key="sk-on-model")).insert()
		self.assertEqual(model_config(m.name)["api_key"], "sk-on-model")

	def test_disabled_provider_not_used(self):
		frappe.get_doc(_provider(api_key="sk-from-provider", enabled=0)).insert()
		m = frappe.get_doc(_model()).insert()
		self.assertIsNone(model_config(m.name)["api_key"])

	def test_no_provider_row_leaves_key_empty(self):
		m = frappe.get_doc(_model()).insert()
		self.assertIsNone(model_config(m.name)["api_key"])

	def test_provider_base_url_used_when_model_has_none(self):
		frappe.get_doc(_provider(base_url="http://gateway.local")).insert()
		m = frappe.get_doc(_model()).insert()
		self.assertEqual(model_config(m.name)["api_base"], "http://gateway.local")


class TestClaudeCodeProvider(IntegrationTestCase):
	def setUp(self):
		frappe.db.delete("Flow Model", {"provider": "claude-code"})
		frappe.db.delete("Flow Provider", "claude-code")

	def tearDown(self):
		frappe.db.rollback()

	def test_claude_code_models_need_no_litellm_and_carry_the_providers_token(self):
		frappe.get_doc(_provider(provider="claude-code", api_key="oauth-token")).insert()
		for model_id in ("opus", "sonnet", "opus[1m]"):
			m = frappe.get_doc(
				_model(title=f"Test Claude Code {model_id}", provider="claude-code", model_id=model_id)
			).insert()
			config = model_config(m.name)
			self.assertEqual(config["model"], f"claude-code/{model_id}")
			self.assertEqual(config["api_key"], "oauth-token")

	def test_without_a_token_claude_code_uses_its_cli_login(self):
		frappe.get_doc(_provider(provider="claude-code", api_key="")).insert()
		m = frappe.get_doc(_model(title="Test Claude Code", model_id="claude-code/opus")).insert()
		self.assertIsNone(model_config(m.name)["api_key"])
