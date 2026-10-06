"""Coverage tests for app.core.engine.memory_pressure.

Self-contained, deterministic, no network / external services.
"""

from __future__ import annotations

from app.core.engine.memory_pressure import (
    CompressionStrategy,
    MemoryPressureConfig,
    MemoryPressureManager,
    PressureSnapshot,
)


# --------------------------------------------------------------------------- #
# Config / strategy enums
# --------------------------------------------------------------------------- #
def test_compression_strategy_values():
    assert {s.value for s in CompressionStrategy} == {
        "summarize",
        "drop_tool_results",
        "keep_system",
        "truncate",
    }


def test_config_defaults():
    cfg = MemoryPressureConfig()
    assert cfg.warning_threshold == 0.75
    assert cfg.critical_threshold == 0.90
    assert cfg.max_messages_keep == 20
    assert cfg.min_messages_keep == 4
    assert cfg.system_message_budget == 4000
    assert cfg.tool_result_max_tokens == 2000
    assert cfg.compression_cooldown_turns == 2
    assert cfg.strategies == [
        CompressionStrategy.TRUNCATE,
        CompressionStrategy.DROP_TOOL_RESULTS,
        CompressionStrategy.SUMMARIZE,
    ]


def test_snapshot_to_dict():
    snap = PressureSnapshot(
        total_tokens=100,
        max_tokens=200,
        usage_ratio=0.5,
        message_count=3,
        tool_result_tokens=40,
        system_tokens=10,
        is_warning=True,
        is_critical=False,
        compression_count=1,
    )
    d = snap.to_dict()
    assert d["total_tokens"] == 100
    assert d["usage_ratio"] == 0.5
    assert d["is_warning"] is True
    assert d["is_critical"] is False
    assert d["compression_count"] == 1


# --------------------------------------------------------------------------- #
# check_pressure / needs_compression / should_alert / reset
# --------------------------------------------------------------------------- #
def _msg(role: str, n: int = 4) -> dict:
    return {"role": role, "content": "x" * n}


def test_check_pressure_levels():
    mgr = MemoryPressureManager()
    # 400 chars -> 100 tokens, max 1000 -> 0.1 ratio, no warning.
    low = mgr.check_pressure([_msg("user", 400)], 1000)
    assert low.usage_ratio == 0.1
    assert low.is_warning is False and low.is_critical is False

    # 320 chars -> 80 tokens, max 100 -> 0.8 -> warning only.
    warn = mgr.check_pressure([_msg("user", 320)], 100, current_turn=3)
    assert warn.is_warning is True and warn.is_critical is False

    # 400 chars -> 100 tokens, max 100 -> 1.0 -> critical.
    crit = mgr.check_pressure([_msg("user", 400)], 100)
    assert crit.is_critical is True


def test_check_pressure_zero_max_tokens():
    mgr = MemoryPressureManager()
    snap = mgr.check_pressure([_msg("user", 400)], 0)
    assert snap.usage_ratio == 0.0
    assert snap.is_warning is False


def test_check_pressure_counts_tool_and_system_tokens():
    mgr = MemoryPressureManager()
    messages = [
        {"role": "system", "content": "s" * 40},  # 10 tokens
        {"role": "tool", "content": "t" * 40},  # 10 tokens
        {"role": "user", "content": "u" * 40},  # 10 tokens
    ]
    snap = mgr.check_pressure(messages, 1000)
    assert snap.system_tokens == 10
    assert snap.tool_result_tokens == 10
    assert snap.message_count == 3
    assert snap.total_tokens == 30


def test_needs_compression_no_pressure():
    mgr = MemoryPressureManager()
    assert mgr.needs_compression([_msg("user", 40)], 1000) is False


def test_needs_compression_critical_always_true():
    mgr = MemoryPressureManager()
    assert mgr.needs_compression([_msg("user", 400)], 100) is True


def test_needs_compression_warning_cooldown():
    mgr = MemoryPressureManager()
    # ratio 0.625 -> warning (0.75? no): use config with lower warning threshold.
    mgr = MemoryPressureManager(MemoryPressureConfig(warning_threshold=0.5, critical_threshold=0.9))
    # 100 tokens / 200 = 0.5 -> warning.
    assert mgr.needs_compression([_msg("user", 400)], 200, current_turn=5) is True

    mgr._last_compression_turn = 5
    # turns_since_last = 0 < cooldown(2) -> False
    assert mgr.needs_compression([_msg("user", 400)], 200, current_turn=5) is False


def test_should_alert_dedup_and_reset():
    mgr = MemoryPressureManager()
    assert mgr.should_alert() is True
    assert mgr.should_alert() is False
    mgr.reset()
    assert mgr.should_alert() is True


# --------------------------------------------------------------------------- #
# token estimators
# --------------------------------------------------------------------------- #
def test_estimate_tokens_with_tool_calls():
    messages = [
        {
            "role": "assistant",
            "content": "abcd",
            "tool_calls": [{"function": {"arguments": "e" * 8}}],
        },
        {"role": "user", "content": "efgh"},
        {"role": "user"},  # no content key
    ]
    # 1 + 2 + 1 = 4
    assert MemoryPressureManager._estimate_tokens(messages) == 4


def test_estimate_tokens_non_string_content():
    # Non-string content is ignored (isinstance content check false branch).
    messages = [{"role": "user", "content": 12345}]
    assert MemoryPressureManager._estimate_tokens(messages) == 0


def test_count_tool_and_system_tokens():
    messages = [
        {"role": "tool", "content": "x" * 8},
        {"role": "system", "content": "y" * 12},
        {"role": "user", "content": "z" * 100},
    ]
    assert MemoryPressureManager._count_tool_result_tokens(messages) == 2
    assert MemoryPressureManager._count_system_tokens(messages) == 3


# --------------------------------------------------------------------------- #
# individual strategies
# --------------------------------------------------------------------------- #
def test_apply_truncate():
    mgr = MemoryPressureManager(MemoryPressureConfig(tool_result_max_tokens=2))
    messages = [
        {"role": "tool", "content": "x" * 100},  # 25 > 2 -> truncated
        {"role": "tool", "content": "short"},  # 1 token -> untouched
        {"role": "user", "content": "keep me"},
    ]
    out = mgr._apply_truncate(messages)
    assert out[0]["content"].endswith("... [truncated]")
    assert len(out[0]["content"]) == 2 * 4 + len("\n... [truncated]")
    assert out[1] == messages[1]
    assert out[2] == messages[2]
    # original list is not mutated in place for the truncated entry
    assert messages[0]["content"] == "x" * 100


def test_apply_drop_tool_results_short_list_unchanged():
    mgr = MemoryPressureManager(MemoryPressureConfig(max_messages_keep=20))
    messages = [_msg("user"), _msg("user")]
    assert mgr._apply_drop_tool_results(messages) == messages


def test_apply_drop_tool_results_trims():
    mgr = MemoryPressureManager(MemoryPressureConfig(max_messages_keep=4))
    messages = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "u1"},
        {"role": "user", "content": "u2"},
        {"role": "user", "content": "u3"},
        {"role": "user", "content": "u4"},
    ]
    out = mgr._apply_drop_tool_results(messages)
    assert out[0]["role"] == "system"
    assert out[-1]["content"] == "u4"
    assert len(out) == 4


def test_apply_keep_system():
    mgr = MemoryPressureManager(MemoryPressureConfig(min_messages_keep=4))
    messages = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "u1"},
        {"role": "user", "content": "u2"},
        {"role": "user", "content": "u3"},
        {"role": "user", "content": "u4"},
        {"role": "user", "content": "u5"},
    ]
    out = mgr._apply_keep_system(messages)
    # keep_count = max(4 - 1, 2) = 3 -> system + last 3 non-system
    assert [m.get("content") for m in out] == ["sys", "u3", "u4", "u5"]


def test_apply_keep_system_floor_of_two():
    mgr = MemoryPressureManager(MemoryPressureConfig(min_messages_keep=0))
    messages = [_msg("user") for _ in range(5)]
    out = mgr._apply_keep_system(messages)
    # keep_count = max(0 - 0, 2) = 2
    assert len(out) == 2


def test_apply_summarize_below_min_returns_same():
    mgr = MemoryPressureManager(MemoryPressureConfig(min_messages_keep=4))
    messages = [_msg("user"), _msg("user")]
    assert mgr._apply_summarize(messages) == messages


def test_apply_summarize_collapses_older_messages():
    mgr = MemoryPressureManager(MemoryPressureConfig(min_messages_keep=3))
    messages = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "old1"},
        {"role": "user", "content": "old2"},
        {"role": "user", "content": "recent1"},
        {"role": "user", "content": "recent2"},
    ]
    out = mgr._apply_summarize(messages)
    assert out[0]["content"] == "sys"
    assert out[1]["role"] == "system"
    assert "Previous context summary" in out[1]["content"]
    assert [m.get("content") for m in out[2:]] == ["recent1", "recent2"]


def test_apply_summarize_empty_non_system_returns_same():
    # keep_count <= 0 and no non-system messages -> to_summarize is empty.
    mgr = MemoryPressureManager(MemoryPressureConfig(min_messages_keep=2))
    messages = [
        {"role": "system", "content": "s1"},
        {"role": "system", "content": "s2"},
        {"role": "system", "content": "s3"},
    ]
    assert mgr._apply_summarize(messages) == messages


def test_apply_summarize_keep_count_zero_with_non_system():
    # keep_count <= 0 but there are non-system messages: all are summarised.
    mgr = MemoryPressureManager(MemoryPressureConfig(min_messages_keep=2))
    messages = [
        {"role": "system", "content": "s1"},
        {"role": "system", "content": "s2"},
        {"role": "user", "content": "u1"},
        {"role": "user", "content": "u2"},
    ]
    out = mgr._apply_summarize(messages)
    assert out[0]["content"] == "s1"
    assert out[1]["content"] == "s2"
    assert out[2]["role"] == "system"
    assert "Previous context summary" in out[2]["content"]


# --------------------------------------------------------------------------- #
# Tests for MemoryPressureManager.compress()
# --------------------------------------------------------------------------- #
def test_compress_below_threshold_applies_nothing():
    mgr = MemoryPressureManager()
    messages = [_msg("user", 8)]
    compressed, report = mgr.compress(messages, max_tokens=1000, current_turn=1)
    assert report["strategies_applied"] == []
    assert report["compression_number"] == 1
    assert mgr._compression_count == 1
    assert mgr._last_compression_turn == 1
    assert compressed == messages


def test_compress_truncate_strategy():
    mgr = MemoryPressureManager(
        MemoryPressureConfig(
            warning_threshold=0.5,
            tool_result_max_tokens=2,
            strategies=[CompressionStrategy.TRUNCATE],
        )
    )
    messages = [{"role": "tool", "content": "x" * 400}]
    compressed, report = mgr.compress(messages, max_tokens=10, current_turn=1)
    assert report["strategies_applied"] == ["truncate"]
    assert compressed[0]["content"].endswith("... [truncated]")
    assert report["compressed_tokens"] < report["original_tokens"]
    assert report["reduction_pct"] > 0


def test_compress_drop_tool_results_strategy():
    mgr = MemoryPressureManager(
        MemoryPressureConfig(
            warning_threshold=0.0,
            max_messages_keep=2,
            strategies=[CompressionStrategy.DROP_TOOL_RESULTS],
        )
    )
    messages = [
        {"role": "system", "content": "s" * 40},
        {"role": "user", "content": "a" * 40},
        {"role": "user", "content": "b" * 40},
        {"role": "tool", "content": "c" * 40},
        {"role": "tool", "content": "d" * 40},
    ]
    _compressed, report = mgr.compress(messages, max_tokens=0, current_turn=2)
    assert report["strategies_applied"] == ["drop_tool_results"]
    assert report["compressed_messages"] < report["original_messages"]


def test_compress_keep_system_strategy():
    mgr = MemoryPressureManager(
        MemoryPressureConfig(
            warning_threshold=0.0,
            min_messages_keep=2,
            strategies=[CompressionStrategy.KEEP_SYSTEM],
        )
    )
    messages = [{"role": "user", "content": "x" * 40} for _ in range(6)]
    _compressed, report = mgr.compress(messages, max_tokens=0, current_turn=3)
    assert report["strategies_applied"] == ["keep_system"]
    assert report["compressed_messages"] == 2


def test_compress_summarize_strategy():
    mgr = MemoryPressureManager(
        MemoryPressureConfig(
            warning_threshold=0.0,
            min_messages_keep=2,
            strategies=[CompressionStrategy.SUMMARIZE],
        )
    )
    messages = [{"role": "user", "content": "msg " + str(i)} for i in range(6)]
    compressed, report = mgr.compress(messages, max_tokens=0, current_turn=4)
    assert report["strategies_applied"] == ["summarize"]
    assert any(
        m.get("role") == "system" and "Previous context summary" in str(m.get("content"))
        for m in compressed
    )


def test_compress_multiple_strategies_and_alert_reset():
    mgr = MemoryPressureManager(
        MemoryPressureConfig(
            warning_threshold=0.5,
            tool_result_max_tokens=2,
            max_messages_keep=3,
            min_messages_keep=2,
            strategies=[
                CompressionStrategy.TRUNCATE,
                CompressionStrategy.DROP_TOOL_RESULTS,
                CompressionStrategy.SUMMARIZE,
            ],
        )
    )
    assert mgr.should_alert() is True
    messages = [
        {"role": "system", "content": "s" * 20},
        {"role": "tool", "content": "t" * 400},
        {"role": "user", "content": "u1"},
        {"role": "user", "content": "u2"},
        {"role": "user", "content": "u3"},
    ]
    compressed, report = mgr.compress(messages, max_tokens=5, current_turn=7)
    assert report["strategies_applied"] == ["truncate", "drop_tool_results", "summarize"]
    assert report["compression_number"] == 1
    # compress() clears the alert flag for the new session.
    assert mgr.should_alert() is True
    # Second compression increments the counter and updates the turn.
    _, report2 = mgr.compress(compressed, max_tokens=1, current_turn=9)
    assert report2["compression_number"] == 2
    assert mgr._last_compression_turn == 9


def test_compress_unknown_strategy_is_skipped():
    # An unrecognised strategy falls through the whole if/elif chain.
    mgr = MemoryPressureManager(
        MemoryPressureConfig(
            warning_threshold=0.0,
            strategies=["bogus"],  # type: ignore[list-item]
        )
    )
    messages = [{"role": "user", "content": "x" * 400}]
    compressed, report = mgr.compress(messages, max_tokens=0, current_turn=1)
    assert report["strategies_applied"] == []
    assert compressed == messages


def test_reset_clears_state():
    mgr = MemoryPressureManager()
    mgr._compression_count = 5
    mgr._last_compression_turn = 9
    mgr._alerted_this_session = True
    mgr.reset()
    assert mgr._compression_count == 0
    assert mgr._last_compression_turn == -100
    assert mgr._alerted_this_session is False
