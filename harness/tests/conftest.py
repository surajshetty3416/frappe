import os

# litellm's bundled model map; the live one changes upstream without notice
os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")

import pytest


@pytest.fixture(autouse=True)
def no_installed_provider_clis(monkeypatch):
	"""A developer's installed `claude` must not configure a provider in tests."""
	monkeypatch.setattr("flow_harness.model.catalog._cli_installed", lambda provider: False)
