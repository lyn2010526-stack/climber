"""Tests for tool error redaction and MemFS path containment."""

from __future__ import annotations

import pytest

from app.core.memfs.store import MemFS
from app.tools import ToolRegistry, redact_error_text


class TestRedactErrorText:
    def test_redacts_prefixed_provider_keys(self):
        for secret in (
            "sk-abcdefghijklmnopqrstuvwxyz01",
            "ghp_abcdefghijklmnopqrstuvwxyz01",
            "github_pat_abcdefghijklmnopqrstuvwxyz01",
        ):
            result = redact_error_text(f"request failed with {secret}")
            assert "[REDACTED]" in result
            assert secret not in result

    def test_redacts_bearer_header_value(self):
        bearer_value = "eyJhbGciOiJIUzI1NiJ9.payloadpart.signature"
        result = redact_error_text(f"Authorization: Bearer {bearer_value}")
        assert bearer_value not in result
        assert "[REDACTED]" in result

    def test_redacts_bare_bearer_scheme(self):
        bearer_value = "eyJhbGciOiJIUzI1NiJ9.payloadpart.signature"
        result = redact_error_text(f"upstream said Bearer {bearer_value} expired")
        assert bearer_value not in result
        assert "Bearer" in result

    @pytest.mark.parametrize(
        "message",
        [
            'api_key="hunter2secretvalue"',
            "password: hunter2secretvalue",
            "token=abcdef123456",
            "secret : abcdef123456",
        ],
    )
    def test_redacts_labelled_secrets(self, message):
        result = redact_error_text(message)
        assert "hunter2secretvalue" not in result
        assert "abcdef123456" not in result
        assert "[REDACTED]" in result

    def test_preserves_label_around_redaction(self):
        result = redact_error_text('api_key="leaked-value"')
        assert result.startswith("api_key=")

    def test_preserves_ordinary_error_text(self):
        for message in (
            "connection refused to db:5432",
            "Tool 'fetch_url' not found",
            "普通中文错误信息",
            "HTTP 500 from upstream",
            "",
        ):
            assert redact_error_text(message) == message

    def test_accepts_exception_instances(self):
        error = ValueError("boom api_key=abcdef123456")
        result = redact_error_text(error)
        assert "abcdef123456" not in result
        assert "boom" in result

    def test_non_string_input_is_stringified(self):
        assert redact_error_text(404) == "404"


class TestRegistryExecuteRedaction:
    async def test_execute_masks_secret_in_tool_error(self):
        registry = ToolRegistry()

        def leaky_tool() -> str:
            raise RuntimeError("upstream rejected api_key=supersecret1234")

        registry.register("leaky", "raises", {}, leaky_tool)
        result = await registry.execute("leaky", {})

        assert "supersecret1234" not in result
        assert "[REDACTED]" in result

    async def test_execute_returns_tool_result_unchanged(self):
        registry = ToolRegistry()
        registry.register("ok", "works", {}, lambda: "plain result")
        assert await registry.execute("ok", {}) == "plain result"

    async def test_unknown_tool_raises(self):
        registry = ToolRegistry()
        with pytest.raises(ValueError, match="not found"):
            await registry.execute("missing", {})
