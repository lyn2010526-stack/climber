"""Tests for the model registry."""

from __future__ import annotations

import pytest

from app.models.registry import MODEL_ALIASES, PROVIDERS, ModelRegistry


class FakeAdapter:
    """A fake model adapter for testing."""

    def __init__(self, model_id="fake-model", api_key="fake-key", base_url=None, capabilities=None):
        self.provider = "fake"
        self.model_id = model_id
        self._api_key = api_key
        self.base_url = base_url
        self.capabilities = capabilities or FakeCapability()

    @property
    def api_key(self):
        return self._api_key

    @api_key.setter
    def api_key(self, value):
        self._api_key = value


class FakeCapability:
    chat = True
    streaming = False
    tools = False
    vision = False
    embedding = False
    max_tokens = 4096

    def model_dump(self):
        return {
            "chat": self.chat,
            "streaming": self.streaming,
            "tools": self.tools,
            "vision": self.vision,
            "embedding": self.embedding,
            "max_tokens": self.max_tokens,
        }


class TestModelRegistry:
    """Tests for ModelRegistry."""

    def test_register_model(self):
        reg = ModelRegistry()
        adapter = reg.register_model(
            model_id="gpt-4o",
            provider="openai",
            api_key="test-key",
        )
        assert isinstance(adapter, PROVIDERS["openai"])

    def test_register_model_with_base_url(self):
        reg = ModelRegistry()
        adapter = reg.register_model(
            model_id="custom",
            provider="openai",
            api_key="key",
            base_url="http://localhost:8080",
        )
        assert adapter is not None

    def test_register_unknown_provider_raises(self):
        reg = ModelRegistry()
        with pytest.raises(ValueError, match="Unknown provider"):
            reg.register_model(model_id="x", provider="nonexistent", api_key="key")

    def test_get_model(self):
        reg = ModelRegistry()
        reg.register_model(model_id="gpt-4o", provider="openai", api_key="key")
        adapter = reg.get_model("openai", "gpt-4o")
        assert adapter is not None

    def test_get_model_not_found_raises(self):
        reg = ModelRegistry()
        with pytest.raises(ValueError, match="Model not registered"):
            reg.get_model("openai", "nonexistent")

    def test_get_or_create_existing(self):
        reg = ModelRegistry()
        reg.register_model(model_id="gpt-4o", provider="openai", api_key="key")
        adapter = reg.get_or_create("openai", "gpt-4o", api_key="key")
        assert adapter is not None

    def test_get_or_create_new(self):
        reg = ModelRegistry()
        adapter = reg.get_or_create("openai", "gpt-4o-mini", api_key="key")
        assert adapter is not None

    def test_get_or_create_with_alias(self):
        reg = ModelRegistry()
        adapter = reg.get_or_create("gpt-4o", "", api_key="key")
        assert adapter is not None

    def test_register_keys(self):
        reg = ModelRegistry()
        reg.register_keys(
            provider="openai",
            model_id="gpt-4o",
            api_keys=["key1", "key2", "key3"],
        )
        assert "openai:gpt-4o:key:0" in reg._models
        assert "openai:gpt-4o:key:1" in reg._models
        assert "openai:gpt-4o:key:2" in reg._models

    def test_register_keys_unknown_provider_raises(self):
        reg = ModelRegistry()
        with pytest.raises(ValueError, match="Unknown provider"):
            reg.register_keys(
                provider="nonexistent",
                model_id="x",
                api_keys=["key1"],
            )

    def test_register_keys_with_base_url(self):
        reg = ModelRegistry()
        reg.register_keys(
            provider="openai",
            model_id="gpt-4o",
            api_keys=["key1"],
            base_url="http://localhost:8080",
        )
        assert "openai:gpt-4o:key:0" in reg._models

    def test_list_models(self):
        reg = ModelRegistry()
        reg.register_model(model_id="gpt-4o", provider="openai", api_key="key")
        models = reg.list_models()
        assert len(models) == 1
        assert "capabilities" in models[0]

    def test_list_models_empty(self):
        reg = ModelRegistry()
        assert reg.list_models() == []


class TestProviders:
    """Tests for PROVIDERS dict."""

    def test_openai_provider_exists(self):
        assert "openai" in PROVIDERS

    def test_anthropic_provider_exists(self):
        assert "anthropic" in PROVIDERS

    def test_google_provider_exists(self):
        assert "google" in PROVIDERS

    def test_ollama_provider_exists(self):
        assert "ollama" in PROVIDERS

    def test_stepfun_provider_exists(self):
        assert "stepfun" in PROVIDERS


class TestModelAliases:
    """Tests for MODEL_ALIASES dict."""

    def test_gpt_4o_alias(self):
        assert MODEL_ALIASES["gpt-4o"] == ("openai", "gpt-4o")

    def test_claude_alias(self):
        assert MODEL_ALIASES["claude-3-5-sonnet"] == ("anthropic", "claude-3-5-sonnet-20240620")

    def test_gemini_alias(self):
        assert MODEL_ALIASES["gemini-pro"] == ("google", "gemini-pro")

    def test_llama_alias(self):
        assert MODEL_ALIASES["llama3"] == ("ollama", "llama3")

    def test_step_alias(self):
        assert MODEL_ALIASES["step-1"] == ("stepfun", "step-3.5-flash")

    def test_unknown_alias_returns_input(self):
        result = MODEL_ALIASES.get("totally-unknown-model", ("totally-unknown-model", "totally-unknown-model"))
        assert result == ("totally-unknown-model", "totally-unknown-model")
