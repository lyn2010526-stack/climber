"""TurnState state machine — tracks the lifecycle of a single agent turn.

States:
- PENDING: turn created, not yet started
- RUNNING: actively processing (ReAct loop executing)
- AWAITING_APPROVAL: paused for human approval (ApprovalGate)
- COMPLETED: turn finished successfully
- FAILED: turn ended with error
- CANCELLED: turn cancelled by user/system
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

import structlog

logger = structlog.get_logger()


class TurnState(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


TURN_TRANSITIONS: dict[TurnState, set[TurnState]] = {
    TurnState.PENDING: {TurnState.RUNNING, TurnState.CANCELLED},
    TurnState.RUNNING: {TurnState.AWAITING_APPROVAL, TurnState.COMPLETED, TurnState.FAILED, TurnState.CANCELLED},
    TurnState.AWAITING_APPROVAL: {TurnState.RUNNING, TurnState.COMPLETED, TurnState.FAILED, TurnState.CANCELLED},
    TurnState.COMPLETED: set(),
    TurnState.FAILED: set(),
    TurnState.CANCELLED: set(),
}


def can_transition(from_state: TurnState, to_state: TurnState) -> bool:
    return to_state in TURN_TRANSITIONS.get(from_state, set())


@dataclass
class TurnStateRecord:
    turn_id: str
    state: TurnState
    session_id: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "turn_id": self.turn_id,
            "state": self.state.value,
            "session_id": self.session_id,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
        }


class TurnStateMachine:
    """State machine for individual turn lifecycle."""

    def __init__(self, turn_id: str, session_id: str, initial_state: TurnState = TurnState.PENDING):
        self.record = TurnStateRecord(
            turn_id=turn_id,
            state=initial_state,
            session_id=session_id,
        )

    def transition(self, new_state: TurnState, error: str | None = None) -> bool:
        if not can_transition(self.record.state, new_state):
            logger.warning(
                "invalid_turn_transition",
                turn_id=self.record.turn_id,
                from_state=self.record.state.value,
                to_state=new_state.value,
            )
            return False

        old_state = self.record.state
        self.record.state = new_state

        if new_state == TurnState.RUNNING and self.record.started_at is None:
            self.record.started_at = datetime.now(UTC)

        if new_state in (TurnState.COMPLETED, TurnState.FAILED, TurnState.CANCELLED):
            self.record.completed_at = datetime.now(UTC)

        if error:
            self.record.error = error

        logger.info(
            "turn_state_changed",
            turn_id=self.record.turn_id,
            from_state=old_state.value,
            to_state=new_state.value,
        )
        return True

    @property
    def is_terminal(self) -> bool:
        return self.record.state in (TurnState.COMPLETED, TurnState.FAILED, TurnState.CANCELLED)
