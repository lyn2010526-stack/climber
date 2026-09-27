"""Tool result replay policy tests.

A checkpoint stores `tool_results` alongside the message history, but nothing
consumes them on recovery. Replaying those results is only sound for tools
that are free of side effects: re-running a `read_file` returns the same bytes,
while re-running `write_file` would overwrite a file that may have been
changed since, and re-running `run_command` would repeat whatever the command
did.

The safe rule is derived from the classification tables that already gate
execution (app/core/engine/validation.py), not from a hand-written tool list,
so a newly added tool is covered the moment it is classified.

These tests pin that rule: reads replay, writes and commands do not, an
unknown tool does not, and callers can opt in explicitly.
"""

from __future__ import annotations

import pytest

from app.core.checkpoint import CheckpointData, InMemoryCheckpointStore
from app.core.recovery import RecoveryManager
from app.core.replay import ToolReplayPolicy


def test_read_only_tools_are_replayable() -> None:
    policy = ToolReplayPolicy()
    assert policy.is_replayable("read_file") is True
    assert policy.is_replayable("list_files") is True


def test_write_tools_are_never_replayed() -> None:
    policy = ToolReplayPolicy()
    for name in ("write_file", "append_file", "edit_file", "apply_patch", "download_file"):
        assert policy.is_replayable(name) is False, f"{name} must not replay"


def test_command_tools_are_never_replayed() -> None:
    policy = ToolReplayPolicy()
    for name in ("run_command", "stream_command", "container_exec"):
        assert policy.is_replayable(name) is False, f"{name} must not replay"


def test_unknown_tools_default_to_unsafe() -> None:
    """A tool nobody classified is assumed to have side effects."""
    policy = ToolReplayPolicy()
    assert policy.is_replayable("some_future_tool") is False


def test_network_tools_are_not_replayed() -> None:
    """A network call is not idempotent even though it is not a write."""
    policy = ToolReplayPolicy()
    for name in ("web_search", "fetch_url", "translate"):
        assert policy.is_replayable(name) is False, f"{name} must not replay"


def test_explicit_opt_in_allows_a_callable_tool() -> None:
    policy = ToolReplayPolicy()
    policy.allow("my_idempotent_helper")
    assert policy.is_replayable("my_idempotent_helper") is True


def test_opt_in_does_not_override_the_deny_list() -> None:
    """write_file stays unsafe even if a caller allowlists it by mistake."""
    policy = ToolReplayPolicy()
    policy.allow("write_file")
    assert policy.is_replayable("write_file") is False


def test_filter_returns_only_the_replayable_results() -> None:
    policy = ToolReplayPolicy()
    results = [
        {"tool": "read_file", "result": "contents"},
        {"tool": "write_file", "result": "wrote"},
        {"tool": "list_files", "result": "a, b"},
    ]

    replayable = policy.filter(results)

    assert [r["tool"] for r in replayable] == ["read_file", "list_files"]


def test_filter_handles_entries_without_a_tool_key() -> None:
    policy = ToolReplayPolicy()
    assert policy.filter([{"result": "orphan"}]) == []


def test_filter_ignores_unknown_result_shapes() -> None:
    """Anything that is not a tool result dict is dropped, not guessed at."""
    policy = ToolReplayPolicy()
    assert policy.filter(["a string", 42, None]) == []


def test_replayability_follows_the_execution_classification() -> None:
    """The policy and the execution gate must agree on every classified tool.

    If a tool is classified read for execution but deemed unsafe for replay
    (or the reverse), the two subsystems have drifted apart.
    """
    from app.core.engine.validation import _COMMAND_TOOLS, _FILE_TOOLS

    policy = ToolReplayPolicy()
    for name, entry in _FILE_TOOLS.items():
        mode = entry[1] if len(entry) > 1 else None
        expected = mode == "read" and name not in _COMMAND_TOOLS
        assert policy.is_replayable(name) is expected, f"mismatch for {name} ({mode})"

    for name in _COMMAND_TOOLS:
        assert policy.is_replayable(name) is False, f"{name} is a command tool"


def test_unclassified_registered_tools_are_not_replayable() -> None:
    """Coverage gap check: an unclassified tool must fail closed, not open."""
    from app.core.engine.validation import _COMMAND_TOOLS, _FILE_TOOLS
    from app.tools import get_tool_registry

    policy = ToolReplayPolicy()
    registered = set(get_tool_registry()._tools)
    unclassified = registered - set(_FILE_TOOLS) - set(_COMMAND_TOOLS)
    unsafe = policy._unsafe_names()

    for name in unclassified:
        assert name in unsafe or not policy.is_replayable(name), (
            f"{name} is registered but unclassified and would default to replayable"
        )


@pytest.mark.asyncio
async def test_recovery_injects_safe_results_into_model_context() -> None:
    store = InMemoryCheckpointStore()
    await store.save(
        None,
        CheckpointData(
            session_id="s1",
            messages=[{"role": "user", "content": "read it"}],
            iteration=3,
            status="interrupted",
            tool_results=[
                {"tool": "read_file", "tool_call_id": "call-1", "result": "contents"}
            ],
        ),
    )
    recovered = await RecoveryManager(store).recover_session("s1")
    assert recovered is not None
    assert recovered["messages"][-1] == {
        "role": "tool", "content": "contents", "tool_call_id": "call-1"
    }


@pytest.mark.asyncio
async def test_recovery_withholds_side_effect_results_from_model_context() -> None:
    store = InMemoryCheckpointStore()
    await store.save(
        None,
        CheckpointData(
            session_id="s1",
            messages=[
                {"role": "user", "content": "do it"},
                {"role": "tool", "tool_call_id": "call-write", "content": "wrote"},
                {"role": "tool", "tool_call_id": "call-command", "content": "done"},
            ],
            iteration=3,
            status="interrupted",
            tool_results=[
                {"tool": "write_file", "tool_call_id": "call-write", "result": "wrote"},
                {"tool": "run_command", "tool_call_id": "call-command", "result": "done"},
            ],
        ),
    )
    recovered = await RecoveryManager(store).recover_session("s1")
    assert recovered is not None
    assert recovered["messages"] == [{"role": "user", "content": "do it"}]


@pytest.mark.asyncio
async def test_engine_recovery_restores_injected_safe_result() -> None:
    from app.core.agent_engine import AgentEngine
    from app.core.session import AgentSession

    store = InMemoryCheckpointStore()
    await store.save(
        None,
        CheckpointData(
            session_id="s1",
            messages=[{"role": "user", "content": "read it"}],
            iteration=3,
            status="interrupted",
            tool_results=[{"tool": "read_file", "tool_call_id": "call-1", "result": "contents"}],
        ),
    )
    session = AgentSession(session_id="s1")
    engine = AgentEngine(model_registry=object(), tool_registry=object(), checkpoint_store=store)

    assert await engine.recover_session(session) is True
    assert session.messages[-1]["content"] == "contents"
