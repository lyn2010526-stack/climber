"""Tool failure policy and handler.

Provides structured handling of tool call failures with configurable policies:
- IGNORE: silently continue
- WARN: log warning but continue
- RAISE: raise the error immediately

Also tracks failure counts per tool and enforces max failure limits.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger()


class ToolFailure(BaseModel):
    """Structured tool failure report."""

    message: str
    code: str | None = None
    retryable: bool = False
    tool_name: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    context: dict[str, Any] = Field(default_factory=dict)


class ToolFailurePolicy(StrEnum):
    """Policy for handling tool call failures."""

    IGNORE = "ignore"
    WARN = "warn"
    RAISE = "raise"


class ToolFailureRecord(BaseModel):
    """Record of failures for a specific tool."""

    tool_name: str
    failure_count: int = 0
    failures: list[ToolFailure] = Field(default_factory=list)
    last_failure: datetime | None = None


class ToolFailureHandler:
    """Handle tool call failures according to a policy.

    Tracks failure counts per tool and enforces configurable limits.
    When max_failures is reached for a tool, the handler automatically
    escalates to RAISE regardless of the base policy.
    """

    def __init__(
        self,
        policy: ToolFailurePolicy = ToolFailurePolicy.WARN,
        max_failures: int = 3,
        on_failure: Any = None,
    ):
        self.policy = policy
        self.max_failures = max_failures
        self.on_failure = on_failure
        self._records: dict[str, ToolFailureRecord] = {}

    async def handle(
        self,
        tool_name: str,
        error: Exception,
        context: dict[str, Any] | None = None,
    ) -> ToolFailure:
        """Handle a tool call failure.

        Returns a ToolFailure report. Depending on the policy:
        - IGNORE: logs at debug level and continues
        - WARN: logs at warning level and continues
        - RAISE: raises the original error
        """
        retryable = self._is_retryable(error)
        code = self._extract_error_code(error)

        failure = ToolFailure(
            message=str(error),
            code=code,
            retryable=retryable,
            tool_name=tool_name,
            context=context or {},
        )

        record = self._get_or_create_record(tool_name)
        record.failure_count += 1
        record.failures.append(failure)
        record.last_failure = failure.timestamp

        should_raise = self.policy == ToolFailurePolicy.RAISE
        if record.failure_count >= self.max_failures:
            should_raise = True
            logger.error(
                "tool_max_failures_reached",
                tool_name=tool_name,
                count=record.failure_count,
            )

        if self.on_failure:
            try:
                await self.on_failure(failure)
            except Exception as callback_err:
                logger.error("tool_failure_callback_error", error=str(callback_err))

        if should_raise:
            logger.error(
                "tool_failure_raising",
                tool_name=tool_name,
                error=str(error),
                count=record.failure_count,
            )
            raise error

        if self.policy == ToolFailurePolicy.WARN:
            logger.warning(
                "tool_failure_warned",
                tool_name=tool_name,
                error=str(error),
                count=record.failure_count,
                retryable=retryable,
            )
        else:
            logger.debug(
                "tool_failure_ignored",
                tool_name=tool_name,
                error=str(error),
            )

        return failure

    def get_record(self, tool_name: str) -> ToolFailureRecord | None:
        """Get the failure record for a specific tool."""
        return self._records.get(tool_name)

    def get_all_records(self) -> dict[str, ToolFailureRecord]:
        """Get all failure records."""
        return dict(self._records)

    def reset(self, tool_name: str | None = None) -> None:
        """Reset failure records.

        If tool_name is provided, resets only that tool.
        Otherwise resets all records.
        """
        if tool_name:
            self._records.pop(tool_name, None)
        else:
            self._records = {}

    def _get_or_create_record(self, tool_name: str) -> ToolFailureRecord:
        """Get or create a failure record for a tool."""
        if tool_name not in self._records:
            self._records[tool_name] = ToolFailureRecord(tool_name=tool_name)
        return self._records[tool_name]

    @staticmethod
    def _is_retryable(error: Exception) -> bool:
        """Determine if an error is potentially retryable."""
        retryable_types = (
            TimeoutError,
            ConnectionError,
            OSError,
        )
        if isinstance(error, retryable_types):
            return True
        error_msg = str(error).lower()
        retryable_keywords = [
            "timeout",
            "rate limit",
            "too many requests",
            "connection",
            "temporary",
            "unavailable",
            "503",
            "429",
        ]
        return any(kw in error_msg for kw in retryable_keywords)

    @staticmethod
    def _extract_error_code(error: Exception) -> str | None:
        """Extract an error code from an exception if available."""
        if hasattr(error, "code"):
            return str(error.code)
        if hasattr(error, "status"):
            return str(error.status)
        if hasattr(error, "status_code"):
            return str(error.status_code)
        return None
