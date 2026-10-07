"""Tests for the optional built-in agent profile integration."""

from app.core.agents import get_builtin_agent, list_builtin_agents, resolve_builtin_agent
from app.core.prompt_manager import PromptManager


def test_builtin_profiles_expose_the_initial_contract():
    profile = resolve_builtin_agent("builtin.assistant")

    assert profile.agent_id == "builtin.assistant"
    assert profile.role == "assistant"
    assert profile.system_prompt
    assert profile.context_policy["include_task"] is True
    assert "started" in profile.lifecycle_events

    assert get_builtin_agent("missing") is None
    assert {item.agent_id for item in list_builtin_agents()} >= {
        "builtin.assistant",
        "builtin.reviewer",
    }


def test_prompt_manager_builds_profile_with_prompt_metadata():
    manager = PromptManager()
    bundle = manager.build(
        agent_id="builtin.assistant",
        context={"objective": "inspect the change"},
    )

    assert "engineering assistant" in bundle["system_prompt"]
    assert bundle["system_prompt"]
    assert bundle["metadata"]["agent_id"] == "builtin.assistant"
    assert bundle["metadata"]["prompt_version"]
    assert len(bundle["metadata"]["prompt_hash"]) == 64
    assert bundle["metadata"]["prompt_source"] == "builtin-agent:builtin.assistant"


def test_legacy_prompt_manager_assembly_remains_a_string_api():
    manager = PromptManager()
    manager.register_template("default", "Hello {name}")

    assert manager.assemble_prompt({"name": "Climber"}) == "Hello Climber"
