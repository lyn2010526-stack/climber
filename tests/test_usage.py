"""Tests for usage tracking and rate limiting."""

from __future__ import annotations

import pytest

from app.storage.usage import UsageTracker, UsageRecord


@pytest.fixture
def tracker() -> UsageTracker:
    return UsageTracker(
        requests_per_minute=5,
        tokens_per_day=10_000,
        tool_calls_per_hour=10,
    )


class TestUsageRecord:
    def test_create_record(self):
        record = UsageRecord(
            user_id="user1",
            session_id="sess1",
            provider="openai",
            model_id="gpt-4",
            tokens_used=150,
            tool_calls=2,
        )
        assert record.user_id == "user1"
        assert record.tokens_used == 150
        assert record.tool_calls == 2
        assert record.status == "success"
        assert record.id is not None
        assert record.created_at is not None

    def test_to_dict(self):
        record = UsageRecord(
            user_id="user1",
            session_id="sess1",
            provider="openai",
            model_id="gpt-4",
            tokens_used=100,
        )
        d = record.to_dict()
        assert d["user_id"] == "user1"
        assert d["tokens_used"] == 100
        assert "id" in d
        assert "created_at" in d


class TestUsageTracker:
    @pytest.mark.asyncio
    async def test_record_usage(self, tracker: UsageTracker):
        await tracker.record(
            user_id="user1",
            session_id="sess1",
            provider="openai",
            model_id="gpt-4",
            tokens_used=200,
            tool_calls=3,
        )
        records = tracker.get_user_records("user1")
        assert len(records) == 1
        assert records[0]["tokens_used"] == 200
        assert records[0]["tool_calls"] == 3

    @pytest.mark.asyncio
    async def test_check_rate_limit_allows_under_limit(self, tracker: UsageTracker):
        for _ in range(3):
            await tracker.record(user_id="user1", session_id="s1", provider="openai", model_id="gpt-4")
        allowed, reason = await tracker.check_rate_limit("user1")
        assert allowed is True
        assert reason is None

    @pytest.mark.asyncio
    async def test_check_rate_limit_blocks_requests_per_minute(self, tracker: UsageTracker):
        for _ in range(5):
            await tracker.record(user_id="user1", session_id="s1", provider="openai", model_id="gpt-4")
        allowed, reason = await tracker.check_rate_limit("user1")
        assert allowed is False
        assert "requests/minute" in reason

    @pytest.mark.asyncio
    async def test_check_rate_limit_blocks_daily_tokens(self, tracker: UsageTracker):
        await tracker.record(
            user_id="user2",
            session_id="s1",
            provider="openai",
            model_id="gpt-4",
            tokens_used=10_000,
        )
        allowed, reason = await tracker.check_rate_limit("user2")
        assert allowed is False
        assert "token" in reason.lower()

    @pytest.mark.asyncio
    async def test_check_rate_limit_blocks_hourly_tool_calls(self):
        tracker = UsageTracker(requests_per_minute=100, tool_calls_per_hour=5)
        for _ in range(5):
            await tracker.record(
                user_id="user3",
                session_id="s1",
                provider="openai",
                model_id="gpt-4",
                tool_calls=1,
            )
        allowed, reason = await tracker.check_rate_limit("user3")
        assert allowed is False
        assert "tool call" in reason.lower()

    @pytest.mark.asyncio
    async def test_get_usage_summary(self, tracker: UsageTracker):
        await tracker.record(
            user_id="user1",
            session_id="s1",
            provider="openai",
            model_id="gpt-4",
            tokens_used=500,
            tool_calls=2,
        )
        summary = await tracker.get_usage_summary("user1")
        assert summary["tokens_today"] == 500
        assert summary["tool_calls_last_hour"] == 2
        assert summary["total_requests"] == 1
        assert summary["total_tokens"] == 500
        assert summary["requests_limit"] == 5
        assert summary["tokens_limit"] == 10_000

    @pytest.mark.asyncio
    async def test_get_user_records_limit(self, tracker: UsageTracker):
        for i in range(10):
            await tracker.record(
                user_id="user1",
                session_id=f"s{i}",
                provider="openai",
                model_id="gpt-4",
            )
        records = tracker.get_user_records("user1", limit=5)
        assert len(records) == 5

    def test_cleanup_old_records(self, tracker: UsageTracker):
        record = UsageRecord(
            user_id="user1",
            session_id="s1",
            provider="openai",
            model_id="gpt-4",
        )
        tracker._records.append(record)
        # Manually set created_at to 2 hours ago
        from datetime import datetime, timedelta
        record.created_at = (datetime.utcnow() - timedelta(hours=2)).isoformat()
        removed = tracker.cleanup_old_records(max_age_hours=1)
        assert removed == 1
        assert len(tracker._records) == 0

    @pytest.mark.asyncio
    async def test_separate_user_tracking(self, tracker: UsageTracker):
        await tracker.record(
            user_id="user1",
            session_id="s1",
            provider="openai",
            model_id="gpt-4",
            tokens_used=100,
        )
        await tracker.record(
            user_id="user2",
            session_id="s2",
            provider="anthropic",
            model_id="claude-3",
            tokens_used=200,
        )
        summary1 = await tracker.get_usage_summary("user1")
        summary2 = await tracker.get_usage_summary("user2")
        assert summary1["total_tokens"] == 100
        assert summary2["total_tokens"] == 200
