"""Tests for the external prompt template registry."""

from __future__ import annotations

import pytest

from app.core.prompt_registry import PromptRegistry


@pytest.fixture
def registry(tmp_path):
    return PromptRegistry(prompts_dir=str(tmp_path / "prompts"))


class TestPromptRegistry:
    def test_load_system_prompt(self, registry):
        prompt = registry.get("system")
        assert "AI assistant" in prompt

    def test_variable_substitution(self, registry):
        prompt = registry.get(
            "system", working_directory="/proj", language="Python"
        )
        assert "/proj" in prompt
        assert "Python" in prompt

    def test_load_role_prompt(self, registry):
        prompt = registry.get_role("planner")
        assert "planning" in prompt.lower()

    def test_load_all_default_roles(self, registry):
        for role in ("planner", "coder", "reviewer"):
            prompt = registry.get_role(role)
            assert len(prompt) > 0

    def test_load_template(self, registry):
        tmpl = registry.get_template("code_review", code="x = 1", context="test")
        assert "x = 1" in tmpl
        assert "test" in tmpl

    def test_load_agent_spec(self, tmp_path, registry):
        spec_file = tmp_path / "AGENT_SPEC.md"
        spec_file.write_text("# Project Rules\n- Write tests\n- Use type hints")
        content = registry.load_agent_spec(str(spec_file))
        assert "Write tests" in content

    def test_load_agent_spec_missing(self, tmp_path, registry):
        content = registry.load_agent_spec(str(tmp_path / "NONEXISTENT.md"))
        assert content == ""

    def test_missing_prompt_returns_empty(self, registry):
        prompt = registry.get("nonexistent")
        assert prompt == ""

    def test_list_available(self, registry):
        available = registry.list_available()
        assert "planner" in available["roles"]
        assert "code_review" in available["templates"]

    def test_reload_clears_cache(self, registry):
        registry.get("system")
        assert len(registry._cache) > 0
        registry.reload()
        assert len(registry._cache) == 0

    def test_caching_returns_same_content(self, registry):
        first = registry.get("system")
        second = registry.get("system")
        assert first == second

    def test_safe_substitute_preserves_unset_variables(self, registry):
        prompt = registry.get("system", working_directory="/proj")
        assert "$language" in prompt
        assert "/proj" in prompt

    def test_list_available_includes_all_defaults(self, registry):
        available = registry.list_available()
        assert set(available["roles"]) == {"planner", "coder", "reviewer"}
        assert set(available["templates"]) == {"code_review", "refactoring"}
