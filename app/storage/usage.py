"""Usage tracking and rate limiting."""

from __future__ import annotations

import asyncio
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Any

import structlog

logger = structlog.get_logger()


class UsageRecord:
    """A single API usage record."""

    def __init__(
        self,
        user_id: str,
        session_id: str,
        provider: str,
        model_id: str,
        tokens_used: int = 0,
        tool_calls: int = 0,
        status: str = "success",
    ):
        self.id = str(uuid.uuid4())
        self.user_id = user_id
        self.session_id = session_id
        self.provider = provider
        self.model_id = model_id
        self.tokens_used = tokens_used
        self.tool_calls = tool_calls
        self.status = status
        self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "provider": self.provider,
            "model_id": self.model_id,
            "tokens_used": self.tokens_used,
            "tool_calls": self.tool_calls,
            "status": self.status,
            "created_at": self.created_at,
        }


class UsageTracker:
    """Tracks API usage per user with rate limiting."""

    def __init__(
        self,
        requests_per_minute: int = 30,
        tokens_per_day: int = 1_000_000,
        tool_calls_per_hour: int = 100,
        max_records: int = 10000,
    ):
        self.requests_per_minute = requests_per_minute
        self.tokens_per_day = tokens_per_day
        self.tool_calls_per_hour = tool_calls_per_hour
        self._max_records = max_records
        self._records: list[UsageRecord] = []
        self._request_timestamps: dict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def record(
        self,
        user_id: str,
        session_id: str,
        provider: str,
        model_id: str,
        tokens_used: int = 0,
        tool_calls: int = 0,
        status: str = "success",
    ) -> UsageRecord:
        """Record a usage event."""
        async with self._lock:
            record = UsageRecord(
                user_id=user_id,
                session_id=session_id,
                provider=provider,
                model_id=model_id,
                tokens_used=tokens_used,
                tool_calls=tool_calls,
                status=status,
            )
            self._records.append(record)
            if len(self._records) > self._max_records:
                self._records = self._records[-self._max_records:]
            self._request_timestamps[user_id].append(time.time())
            # Cleanup old timestamps (keep last 24h)
            cutoff = time.time() - 86400
            self._request_timestamps[user_id] = [
                t for t in self._request_timestamps[user_id] if t > cutoff
            ]
            return record

    async def check_rate_limit(self, user_id: str) -> tuple[bool, str | None]:
        """Check if user has exceeded rate limits. Returns (allowed, reason)."""
        async with self._lock:
            now = time.time()

            # Requests per minute
            one_minute_ago = now - 60
            recent_requests = [
                t for t in self._request_timestamps.get(user_id, [])
                if t > one_minute_ago
            ]
            if len(recent_requests) >= self.requests_per_minute:
                return False, f"Rate limit: {self.requests_per_minute} requests/minute exceeded"

            # Tokens per day
            one_day_ago = datetime.now(timezone.utc) - timedelta(days=1)
            daily_tokens = sum(
                r.tokens_used
                for r in self._records
                if r.user_id == user_id
                and datetime.fromisoformat(r.created_at) > one_day_ago
            )
            if daily_tokens >= self.tokens_per_day:
                return False, f"Daily token limit ({self.tokens_per_day}) exceeded"

            # Tool calls per hour
            one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
            hourly_tool_calls = sum(
                r.tool_calls
                for r in self._records
                if r.user_id == user_id
                and datetime.fromisoformat(r.created_at) > one_hour_ago
            )
            if hourly_tool_calls >= self.tool_calls_per_hour:
                return False, f"Hourly tool call limit ({self.tool_calls_per_hour}) exceeded"

            return True, None

    async def get_usage_summary(self, user_id: str) -> dict[str, Any]:
        """Get usage summary for a user."""
        async with self._lock:
            now = datetime.now(timezone.utc)
            one_day_ago = now - timedelta(days=1)
            one_hour_ago = now - timedelta(hours=1)

            user_records = [r for r in self._records if r.user_id == user_id]

            daily_records = [
                r for r in user_records
                if datetime.fromisoformat(r.created_at) > one_day_ago
            ]
            hourly_records = [
                r for r in user_records
                if datetime.fromisoformat(r.created_at) > one_hour_ago
            ]

            return {
                "requests_last_minute": len([
                    t for t in self._request_timestamps.get(user_id, [])
                    if t > time.time() - 60
                ]),
                "requests_limit": self.requests_per_minute,
                "tokens_today": sum(r.tokens_used for r in daily_records),
                "tokens_limit": self.tokens_per_day,
                "tool_calls_last_hour": sum(r.tool_calls for r in hourly_records),
                "tool_calls_limit": self.tool_calls_per_hour,
                "total_requests": len(user_records),
                "total_tokens": sum(r.tokens_used for r in user_records),
            }

    def get_user_records(
        self, user_id: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Get recent usage records for a user."""
        user_records = [r for r in self._records if r.user_id == user_id]
        return [r.to_dict() for r in reversed(user_records[-limit:])]

    def cleanup_old_records(self, max_age_hours: int = 24) -> int:
        """Remove records older than max_age_hours. Returns count removed."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        original_len = len(self._records)
        self._records = [
            r for r in self._records
            if datetime.fromisoformat(r.created_at).replace(tzinfo=timezone.utc) > cutoff
        ]
        removed = original_len - len(self._records)
        if removed > 0:
            logger.info("Cleaned up old usage records", count=removed)
        return removed


# Global singleton
usage_tracker = UsageTracker()
