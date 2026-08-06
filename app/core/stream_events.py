"""Stream events for multi-agent collaboration."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class CollabEventType(StrEnum):
    """Event types for collaboration streaming."""

    # Lifecycle
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_PARTIAL = "task_partial"
    TASK_FAILED = "task_failed"
    TASK_STOPPED = "task_stopped"
    ROUND_START = "round_start"
    ROUND_END = "round_end"

    # Worker events
    WORKER_START = "worker_start"
    WORKER_TOOL_CALL = "worker_tool_call"
    WORKER_TOOL_RESULT = "worker_tool_result"
    WORKER_DONE = "worker_done"

    # Reviewer events
    REVIEWER_START = "reviewer_start"
    REVIEWER_DONE = "reviewer_done"
    REVIEWER_ISSUE = "reviewer_issue"

    # Streaming text
    TEXT_DELTA = "text_delta"
    TEXT_DONE = "text_done"

    # Context management
    CONTEXT_COMPRESSION = "context_compression"

    # Control
    PROGRESS_UPDATE = "progress_update"
    ERROR = "error"


@dataclass
class CollabEvent:
    """A single collaboration event pushed via WebSocket."""

    type: CollabEventType
    session_id: str
    member_id: str | None = None
    member_name: str | None = None
    member_avatar: str | None = None
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for JSON push."""
        return {
            "type": self.type.value,
            "session_id": self.session_id,
            "member_id": self.member_id,
            "member_name": self.member_name,
            "member_avatar": self.member_avatar,
            "data": self.data,
            "timestamp": self.timestamp,
        }


def make_text_delta(session_id: str, member_id: str, member_name: str, delta: str, avatar: str | None = None) -> CollabEvent:
    return CollabEvent(
        type=CollabEventType.TEXT_DELTA,
        session_id=session_id,
        member_id=member_id,
        member_name=member_name,
        member_avatar=avatar,
        data={"delta": delta},
    )


def make_worker_tool_call(session_id: str, member_id: str, member_name: str, tool_name: str, arguments: dict, avatar: str | None = None) -> CollabEvent:
    return CollabEvent(
        type=CollabEventType.WORKER_TOOL_CALL,
        session_id=session_id,
        member_id=member_id,
        member_name=member_name,
        member_avatar=avatar,
        data={"tool_name": tool_name, "arguments": arguments},
    )


def make_worker_tool_result(session_id: str, member_id: str, member_name: str, tool_name: str, result: str, avatar: str | None = None) -> CollabEvent:
    return CollabEvent(
        type=CollabEventType.WORKER_TOOL_RESULT,
        session_id=session_id,
        member_id=member_id,
        member_name=member_name,
        member_avatar=avatar,
        data={"tool_name": tool_name, "result": result},
    )


def make_reviewer_issues(session_id: str, member_id: str, member_name: str, issues: list[dict], avatar: str | None = None) -> CollabEvent:
    return CollabEvent(
        type=CollabEventType.REVIEWER_DONE,
        session_id=session_id,
        member_id=member_id,
        member_name=member_name,
        member_avatar=avatar,
        data={"issues": issues, "passed": len(issues) == 0},
    )


def make_progress(session_id: str, current_round: int, max_rounds: int, status: str, active_member: str | None = None) -> CollabEvent:
    return CollabEvent(
        type=CollabEventType.PROGRESS_UPDATE,
        session_id=session_id,
        data={
            "current_round": current_round,
            "max_rounds": max_rounds,
            "status": status,
            "active_member": active_member,
            "progress_pct": min(int(current_round / max(max_rounds, 1) * 100), 99),
        },
    )


def make_context_compression(
    session_id: str,
    original_tokens: int,
    compressed_tokens: int,
) -> CollabEvent:
    return CollabEvent(
        type=CollabEventType.CONTEXT_COMPRESSION,
        session_id=session_id,
        data={
            "original_tokens": original_tokens,
            "compressed_tokens": compressed_tokens,
            "savings_pct": max(0, int((1 - compressed_tokens / max(original_tokens, 1)) * 100)),
        },
    )


def make_task_completed(session_id: str, final_output: str, total_rounds: int) -> CollabEvent:
    return CollabEvent(
        type=CollabEventType.TASK_COMPLETED,
        session_id=session_id,
        data={"final_output": final_output, "total_rounds": total_rounds},
    )
