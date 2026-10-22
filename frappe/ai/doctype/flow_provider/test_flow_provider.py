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

	def test_a_provider_is_a_known_litellm_name_with_an_http_base_url(self):
		for overrides, error in (
			({"provider": "not-a-real-provider"}, "Unknown provider"),
			({"base_url": "not-a-url"}, "Base URL"),
		):
			with self.subTest(**overrides), self.assertRaisesRegex(frappe.ValidationError, error):
				frappe.get_doc(_provider(**overrides)).insert()
		with self.subTest("named by its lowercase name"):
			doc = frappe.get_doc(_provider(provider="OpenRouter")).insert()
			self.assertEqual((doc.name, doc.provider), ("openrouter", "openrouter"))


class TestProviderCredentialResolution(IntegrationTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_a_model_takes_what_it_lacks_from_its_enabled_provider(self):
		for label, provider, model, key, expected in (
			("the provider's key", {}, {}, "api_key", "sk-from-provider"),
			("the model's own key first", {}, {"api_key": "sk-on-model"}, "api_key", "sk-on-model"),
			("no key from a disabled provider", {"enabled": 0}, {}, "api_key", None),
			("no key without a provider row", None, {}, "api_key", None),
			(
				"the provider's base URL",
				{"base_url": "http://gateway.local"},
				{},
				"api_base",
				"http://gateway.local",
			),
		):
			with self.subTest(label):
				if provider is not None:
					frappe.get_doc(_provider(api_key="sk-from-provider", **provider)).insert()
				doc = frappe.get_doc(_model(**model)).insert()
				self.assertEqual(model_config(doc.name)[key], expected)
			frappe.db.rollback()


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
