"""Tests for memory pressure manager."""

import pytest

from app.core.engine.memory_pressure import (
    CompressionStrategy,
    MemoryPressureConfig,
    MemoryPressureManager,
    PressureSnapshot,
)


class TestMemoryPressureManager:
    def test_check_pressure_normal(self) -> None:
        manager = MemoryPressureManager()
        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"},
        ]
        snapshot = manager.check_pressure(messages, max_tokens=10000)
        assert isinstance(snapshot, PressureSnapshot)
        assert snapshot.is_warning is False
        assert snapshot.is_critical is False

    def test_check_pressure_warning(self) -> None:
        manager = MemoryPressureManager(
            MemoryPressureConfig(warning_threshold=0.5, critical_threshold=0.9),
        )
        # Create messages that exceed 50% of max_tokens
        long_content = "x" * 3000  # ~750 tokens
        messages = [
            {"role": "system", "content": long_content},
            {"role": "user", "content": long_content},
        ]
        snapshot = manager.check_pressure(messages, max_tokens=1000)
        assert snapshot.is_warning is True

    def test_needs_compression_false(self) -> None:
        manager = MemoryPressureManager()
        messages = [{"role": "user", "content": "Hi"}]
        assert manager.needs_compression(messages, max_tokens=10000) is False

    def test_needs_compression_true(self) -> None:
        manager = MemoryPressureManager(
            MemoryPressureConfig(warning_threshold=0.5, compression_cooldown_turns=0),
        )
        long_content = "x" * 3000
        messages = [
            {"role": "system", "content": long_content},
            {"role": "user", "content": long_content},
        ]
        assert manager.needs_compression(messages, max_tokens=500, current_turn=5) is True

    def test_cooldown_prevents_compression(self) -> None:
        manager = MemoryPressureManager(
            MemoryPressureConfig(warning_threshold=0.5, critical_threshold=0.9, compression_cooldown_turns=5),
        )
        # Warning level: ~75% of max_tokens (between warning 0.5 and critical 0.9)
        medium_content = "x" * 3000
        messages = [
            {"role": "system", "content": medium_content},
            {"role": "user", "content": medium_content},
        ]
        # First turn 0 — should compress (warning level, no cooldown)
        assert manager.needs_compression(messages, max_tokens=2000, current_turn=0) is True
        # Actually compress at turn 0 — this starts the cooldown
        compressed, _ = manager.compress(messages, max_tokens=2000, current_turn=0)
        # Turn 1 — cooldown prevents (warning level, within cooldown window)
        assert manager.needs_compression(messages, max_tokens=2000, current_turn=1) is False
        # Turn 6 — cooldown expired, should compress again
        assert manager.needs_compression(messages, max_tokens=2000, current_turn=6) is True

    def test_compress_truncate(self) -> None:
        manager = MemoryPressureManager(
            MemoryPressureConfig(tool_result_max_tokens=10),
        )
        messages = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "query"},
            {"role": "tool", "content": "x" * 10000},  # Very long tool result
        ]
        compressed, report = manager.compress(messages, max_tokens=500, current_turn=0)
        assert "truncate" in report["strategies_applied"]
        assert report["original_tokens"] > report["compressed_tokens"]

    def test_compress_drop_tool_results(self) -> None:
        manager = MemoryPressureManager(
            MemoryPressureConfig(
                warning_threshold=0.3,
                max_messages_keep=3,
                strategies=[CompressionStrategy.DROP_TOOL_RESULTS],
            ),
        )
        messages = [
            {"role": "system", "content": "x" * 500},
            {"role": "user", "content": "x" * 500},
            {"role": "tool", "content": "x" * 500},
            {"role": "tool", "content": "x" * 500},
            {"role": "assistant", "content": "x" * 500},
        ]
        compressed, report = manager.compress(messages, max_tokens=500, current_turn=0)
        assert "drop_tool_results" in report["strategies_applied"]

    def test_compress_summarize(self) -> None:
        manager = MemoryPressureManager(
            MemoryPressureConfig(
                warning_threshold=0.1,
                min_messages_keep=2,
                strategies=[CompressionStrategy.SUMMARIZE],
            ),
        )
        messages = [
            {"role": "system", "content": "sys " + "x" * 200},
            {"role": "user", "content": "msg1 " + "x" * 200},
            {"role": "assistant", "content": "msg2 " + "x" * 200},
            {"role": "user", "content": "msg3 " + "x" * 200},
            {"role": "assistant", "content": "msg4 " + "x" * 200},
        ]
        compressed, report = manager.compress(messages, max_tokens=100, current_turn=0)
        assert "summarize" in report["strategies_applied"]

    def test_should_alert_dedup(self) -> None:
        manager = MemoryPressureManager()
        assert manager.should_alert() is True
        assert manager.should_alert() is False

    def test_reset(self) -> None:
        manager = MemoryPressureManager()
        manager.should_alert()  # Mark as alerted
        manager._compression_count = 3
        manager.reset()
        assert manager._compression_count == 0
        assert manager.should_alert() is True  # Can alert again

    def test_compression_count_increments(self) -> None:
        manager = MemoryPressureManager(
            MemoryPressureConfig(warning_threshold=0.1, compression_cooldown_turns=0),
        )
        messages = [
            {"role": "system", "content": "x" * 1000},
            {"role": "user", "content": "x" * 1000},
        ]
        _, report1 = manager.compress(messages, max_tokens=100, current_turn=0)
        _, report2 = manager.compress(messages, max_tokens=100, current_turn=1)
        assert report1["compression_number"] == 1
        assert report2["compression_number"] == 2

    def test_snapshot_to_dict(self) -> None:
        snapshot = PressureSnapshot(
            total_tokens=500,
            max_tokens=1000,
            usage_ratio=0.5,
            message_count=5,
            tool_result_tokens=200,
            system_tokens=100,
            is_warning=True,
            is_critical=False,
            compression_count=2,
        )
        d = snapshot.to_dict()
        assert d["usage_ratio"] == 0.5
        assert d["is_warning"] is True
        assert d["compression_count"] == 2


class TestMemoryPressureConfig:
    def test_defaults(self) -> None:
        config = MemoryPressureConfig()
        assert config.warning_threshold == 0.75
        assert config.critical_threshold == 0.90
        assert CompressionStrategy.TRUNCATE in config.strategies
