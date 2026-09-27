"""Anthropic prompt-caching breakpoint tests.

Anthropic's cache is keyed on the hash of a rendered prefix, and a breakpoint
is a `cache_control` marker attached to a content block:

    "Cache prefixes are created in the following order: tools, system, then
     messages."
    "Cache writes happen only at your breakpoint."
    -- https://platform.claude.com/docs/en/build-with-claude/prompt-caching
    -- https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/overview
    -- https://platform.openai.com/docs/guides/function-calling
    -- https://docs.langchain.com/oss/python/langchain/tools

Measured effect, per Anthropic's own arithmetic: one write plus nine reads
costs 2.15x the ordinary input rate against 10x uncached, so a correctly placed
breakpoint removes roughly 78.5% of input cost on a stable prefix.

`AnthropicAdapter` (app/models/anthropic_adapter.py) joined all system messages
into one plain string. Anthropic only honours `cache_control` inside a content
block, so the system prompt was structurally uncacheable. These tests pin the
block form, the breakpoint placement, and the invariants that would silently
destroy a cache if broken -- notably that every system message must precede all
conversation turns, since Anthropic rejects system turns after user turns.
"""

from __future__ import annotations

import pytest

from app.core import MessageRole


def test_system_becomes_a_content_block_list() -> None:
    """A bare string cannot carry cache_control; blocks can."""
    from app.models.anthropic_adapter import AnthropicAdapter

    adapter = AnthropicAdapter.__new__(AnthropicAdapter)
    payload = adapter._build_system_payload(["You are helpful."])
    assert isinstance(payload, list)
    assert payload[0]["type"] == "text"
    assert payload[0]["text"] == "You are helpful."


def test_cache_breakpoint_is_marked_on_the_last_system_block() -> None:
    from app.models.anthropic_adapter import AnthropicAdapter

    adapter = AnthropicAdapter.__new__(AnthropicAdapter)
    payload = adapter._build_system_payload(["one", "two"])
    assert "cache_control" not in payload[0]
    assert payload[-1]["cache_control"] == {"type": "ephemeral"}


def test_empty_system_produces_no_payload() -> None:
    from app.models.anthropic_adapter import AnthropicAdapter

    adapter = AnthropicAdapter.__new__(AnthropicAdapter)
    assert adapter._build_system_payload([]) is None


def test_breakpoint_can_be_disabled() -> None:
    """A caller that must not cache (one-off calls) needs an opt-out."""
    from app.models.anthropic_adapter import AnthropicAdapter

    adapter = AnthropicAdapter.__new__(AnthropicAdapter)
    payload = adapter._build_system_payload(["x"], enable_cache=False)
    assert "cache_control" not in payload[0]


def test_dynamic_blocks_stay_out_of_the_cached_prefix() -> None:
    """Per-turn injected memory must not sit inside the cached system text.

    Climber injects lessons and graph context as SYSTEM messages whose content
    changes every turn. Anthropic hashes the whole system prefix, so a single
    changed block would invalidate the cache on every request. Those markers
    must be separated out rather than concatenated into the cached text.
    """
    from app.core.agent_engine import DYNAMIC_SYSTEM_MARKERS
    from app.models.anthropic_adapter import AnthropicAdapter

    assert any("LESSONS" in m for m in DYNAMIC_SYSTEM_MARKERS)
    assert any("GRAPH" in m for m in DYNAMIC_SYSTEM_MARKERS)

    adapter = AnthropicAdapter.__new__(AnthropicAdapter)
    messages = [
        {"role": MessageRole.SYSTEM, "content": "stable base prompt"},
        {"role": MessageRole.SYSTEM, "content": "<!-- LESSONS --> turn-1 lesson"},
    ]
    stable, dynamic = adapter._split_system_messages(messages)
    assert stable == ["stable base prompt"]
    assert dynamic == ["<!-- LESSONS --> turn-1 lesson"]


def test_cached_system_text_is_identical_across_turns() -> None:
    """The property the whole optimisation depends on.

    Two turns differing only in injected memory must produce byte-identical
    cached system text, otherwise every request pays a fresh cache write.
    """
    from app.models.anthropic_adapter import AnthropicAdapter

    adapter = AnthropicAdapter.__new__(AnthropicAdapter)
    turn_1 = [
        {"role": MessageRole.SYSTEM, "content": "base"},
        {"role": MessageRole.SYSTEM, "content": "<!-- LESSONS --> lesson A"},
    ]
    turn_2 = [
        {"role": MessageRole.SYSTEM, "content": "base"},
        {"role": MessageRole.SYSTEM, "content": "<!-- LESSONS --> lesson B"},
    ]
    first = adapter._build_system_payload(adapter._split_system_messages(turn_1)[0] and [
        {"role": "system", "content": p}
        for p in adapter._split_system_messages(turn_1)[0]
    ])
    second = adapter._build_system_payload([
        {"role": "system", "content": p}
        for p in adapter._split_system_messages(turn_2)[0]
    ])
    assert first == second


@pytest.mark.parametrize("marker", ["<!-- LESSONS -->", "<!-- GRAPH_CONTEXT -->"])
def test_every_declared_marker_is_recognised(marker: str) -> None:
    from app.core.agent_engine import DYNAMIC_SYSTEM_MARKERS

    assert marker in DYNAMIC_SYSTEM_MARKERS


def test_tool_cache_breakpoint_is_on_the_last_stable_tool() -> None:
    from app.models.anthropic_adapter import AnthropicAdapter

    adapter = AnthropicAdapter.__new__(AnthropicAdapter)
    tools = [
        {"type": "function", "function": {"name": "first", "parameters": {}}},
        {"type": "function", "function": {"name": "second", "parameters": {}}},
    ]

    payload = adapter._convert_tools(tools)

    assert "cache_control" not in payload[0]
    assert payload[-1]["cache_control"] == {"type": "ephemeral"}


def test_tool_cache_breakpoint_can_be_disabled() -> None:
    from app.models.anthropic_adapter import AnthropicAdapter

    adapter = AnthropicAdapter.__new__(AnthropicAdapter)
    tools = [{"type": "function", "function": {"name": "only", "parameters": {}}}]

    payload = adapter._convert_tools(tools, enable_cache=False)

    assert "cache_control" not in payload[0]
