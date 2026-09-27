"""Tests for session history repair (unpaired tool calls)."""

from __future__ import annotations

from app.core.session_repair import INTERRUPTED_RESULT, repair_unpaired_tool_calls


def _call(call_id: str, name: str = "bash") -> dict:
    return {"id": call_id, "function": {"name": name, "arguments": "{}"}}


def test_paired_history_unchanged():
    msgs = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "", "tool_calls": [_call("a1")]},
        {"role": "tool", "tool_call_id": "a1", "content": "ok"},
    ]
    repaired, inserted = repair_unpaired_tool_calls(msgs)
    assert inserted == 0
    assert repaired is msgs


def test_single_unanswered_call_gets_error_result():
    msgs = [
        {"role": "assistant", "content": "", "tool_calls": [_call("a1")]},
    ]
    repaired, inserted = repair_unpaired_tool_calls(msgs)
    assert inserted == 1
    assert repaired[1]["role"] == "tool"
    assert repaired[1]["tool_call_id"] == "a1"
    assert repaired[1]["content"] == INTERRUPTED_RESULT


def test_multiple_calls_same_message_insert_in_order():
    msgs = [
        {"role": "assistant", "content": "", "tool_calls": [_call("a1"), _call("a2"), _call("a3")]},
        {"role": "tool", "tool_call_id": "a2", "content": "ok"},
    ]
    repaired, inserted = repair_unpaired_tool_calls(msgs)
    assert inserted == 2
    assert [m["tool_call_id"] for m in repaired[1:3]] == ["a1", "a3"]


def test_consecutive_assistants_each_repaired():
    msgs = [
        {"role": "assistant", "content": "", "tool_calls": [_call("a1")]},
        {"role": "assistant", "content": "", "tool_calls": [_call("b1")]},
    ]
    repaired, inserted = repair_unpaired_tool_calls(msgs)
    assert inserted == 2
    assert repaired[1]["tool_call_id"] == "a1"
    assert repaired[3]["tool_call_id"] == "b1"


def test_result_arriving_later_counts_as_answered():
    msgs = [
        {"role": "assistant", "content": "", "tool_calls": [_call("a1")]},
        {"role": "user", "content": "interjection"},
        {"role": "tool", "tool_call_id": "a1", "content": "late result"},
    ]
    repaired, inserted = repair_unpaired_tool_calls(msgs)
    assert inserted == 0
    assert repaired is msgs


def test_call_without_id_ignored():
    msgs = [
        {"role": "assistant", "content": "", "tool_calls": [{"function": {"name": "bash", "arguments": "{}"}}]},
    ]
    repaired, inserted = repair_unpaired_tool_calls(msgs)
    assert inserted == 0
