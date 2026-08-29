"""Tests for bounded agent event replay."""

from __future__ import annotations

import pytest

from app.core.event_replay import EventReplayBuffer


def test_replay_records_have_monotonic_ids_and_copies_payloads():
    buffer = EventReplayBuffer(capacity=3)
    payload = {"content": "hello"}

    record = buffer.append("text", payload)
    payload["content"] = "mutated"

    assert record.sequence == 1
    assert record.event_id == "event-1"
    assert record.turn_id == ""
    assert buffer.after()[0].data == {"content": "hello"}


def test_replay_returns_only_events_after_cursor():
    buffer = EventReplayBuffer(capacity=3)
    for index in range(3):
        buffer.append("text", {"index": index})

    assert [event.sequence for event in buffer.after(1)] == [2, 3]


def test_replay_evicts_oldest_events_by_capacity():
    buffer = EventReplayBuffer(capacity=2)
    for index in range(3):
        buffer.append("text", {"index": index})

    assert buffer.oldest_sequence == 2
    assert [event.sequence for event in buffer.after()] == [2, 3]


def test_replay_evicts_large_payloads_by_byte_budget():
    buffer = EventReplayBuffer(capacity=10, max_bytes=20)
    buffer.append("text", {"content": "a" * 30})

    assert buffer.oldest_sequence is None
    assert buffer.after() == []


def test_replay_empty_buffer_reports_no_sequences():
    buffer = EventReplayBuffer()

    assert buffer.oldest_sequence is None
    assert buffer.latest_sequence == 0
    assert buffer.after(999) == []


def test_replay_cursor_before_evicted_window_returns_retained_suffix():
    buffer = EventReplayBuffer(capacity=2)
    for index in range(4):
        buffer.append("text", {"index": index})

    assert [event.data["index"] for event in buffer.after(1)] == [2, 3]


def test_replay_deep_copies_nested_payloads():
    buffer = EventReplayBuffer()
    payload = {"tool": {"arguments": {"path": "a.txt"}}}
    buffer.append("tool_call", payload)
    payload["tool"]["arguments"]["path"] = "changed.txt"

    assert buffer.after()[0].data["tool"]["arguments"]["path"] == "a.txt"


def test_replay_tracks_latest_sequence_after_eviction():
    buffer = EventReplayBuffer(capacity=1)
    buffer.append("text", {"index": 1})
    buffer.append("done", {"index": 2})

    assert buffer.latest_sequence == 2
    assert buffer.after(1)[0].event_type == "done"


def test_replay_can_filter_events_by_turn():
    buffer = EventReplayBuffer()
    buffer.append("text", {"turn": 1}, turn_id="turn-1")
    buffer.append("done", {"turn": 1}, turn_id="turn-1")
    buffer.append("text", {"turn": 2}, turn_id="turn-2")

    assert [event.data["turn"] for event in buffer.after(turn_id="turn-1")] == [1, 1]


@pytest.mark.parametrize("kwargs", [{"capacity": 0}, {"max_bytes": 0}])
def test_replay_rejects_invalid_limits(kwargs):
    with pytest.raises(ValueError):
        EventReplayBuffer(**kwargs)
