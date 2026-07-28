"""Tests for prompt manager."""

import pytest

from app.core.prompt_manager import PromptManager


@pytest.fixture
def prompt_manager():
    return PromptManager()


class TestPromptManager:
    def test_base_prompt_always_present(self, prompt_manager):
        """Base prompt should always be included."""
        result = prompt_manager.assemble_prompt(autonomous_mode=False, mcp_ready=False)
        assert prompt_manager.base_prompt in result

    def test_autonomous_mode_appends_fragment(self, prompt_manager):
        """Autonomous mode should append autonomous prompt fragment."""
        result = prompt_manager.assemble_prompt(autonomous_mode=True, mcp_ready=False)
        assert prompt_manager.autonomous_prompt in result
        assert "Autonomous Agent Mode" in result

    def test_mcp_ready_appends_constraint(self, prompt_manager):
        """MCP ready should append constraint fragment."""
        result = prompt_manager.assemble_prompt(autonomous_mode=False, mcp_ready=True)
        assert prompt_manager.mcp_constraint_prompt in result
        assert "Token Throttle" in result

    def test_both_modes_combined(self, prompt_manager):
        """Both modes should combine all fragments."""
        result = prompt_manager.assemble_prompt(autonomous_mode=True, mcp_ready=True)
        assert prompt_manager.base_prompt in result
        assert prompt_manager.autonomous_prompt in result
        assert prompt_manager.mcp_constraint_prompt in result

    def test_four_combinations(self, prompt_manager):
        """All four combinations should work."""
        combinations = [
            (False, False, [prompt_manager.base_prompt]),
            (True, False, [prompt_manager.base_prompt, prompt_manager.autonomous_prompt]),
            (False, True, [prompt_manager.base_prompt, prompt_manager.mcp_constraint_prompt]),
            (True, True, [prompt_manager.base_prompt, prompt_manager.autonomous_prompt, prompt_manager.mcp_constraint_prompt]),
        ]

        for auto, mcp, expected_fragments in combinations:
            result = prompt_manager.assemble_prompt(autonomous_mode=auto, mcp_ready=mcp)
            for fragment in expected_fragments:
                assert fragment in result

    def test_get_active_constraints(self, prompt_manager):
        """Test active constraints listing."""
        assert prompt_manager.get_active_constraints(False, False) == []
        assert prompt_manager.get_active_constraints(True, False) == ["autonomous_agent"]
        assert prompt_manager.get_active_constraints(False, True) == ["token_throttle_mcp"]
        assert prompt_manager.get_active_constraints(True, True) == ["autonomous_agent", "token_throttle_mcp"]

    def test_getters(self, prompt_manager):
        """Test individual getters."""
        assert prompt_manager.get_base_prompt() == prompt_manager.base_prompt
        assert prompt_manager.get_autonomous_prompt() == prompt_manager.autonomous_prompt
        assert prompt_manager.get_mcp_constraint_prompt() == prompt_manager.mcp_constraint_prompt
