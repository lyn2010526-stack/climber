"""Checkpoint management for group collaboration task resumption."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import select, update

from app.core.group_ws_hub import group_ws_hub
from app.storage import async_session
from app.storage.models_groups import AgentGroupTask, AgentGroupTaskCheckpoint

logger = structlog.get_logger(__name__)

#: Checkpoint states a task can be resumed from. ``resuming`` is the claimed
#: state written by :func:`claim_checkpoint_for_resume`; a crashed resumer's
#: checkpoint becomes reclaimable again once its lease expires.
RESUMABLE_CHECKPOINT_STATUSES = frozenset({"running", "paused", "resuming"})

#: Status recorded on a checkpoint once the task reached a terminal state.
TERMINAL_CHECKPOINT_STATUSES = frozenset({"completed", "failed", "stopped"})

#: How long a claimed checkpoint stays owned by the resumer that claimed it.
#: Longer than any single round so a live resumer is never preempted.
RESUME_LEASE_SECONDS = 900

_LEASE_KEY = "resume_started_at"


@dataclass(frozen=True)
class ResumeState:
    """State a resumed run needs in order to continue the next round.

    Attributes:
        checkpoint_id: The checkpoint the run resumed from.
        round: Number of rounds already completed.
        max_rounds: Round budget captured when the checkpoint was written.
        worker_output: Accumulated worker output from the completed rounds.
        all_issues: Outstanding reviewer/guardrail issues from the last round.
    """

    checkpoint_id: str
    round: int
    max_rounds: int
    worker_output: str = ""
    all_issues: list[dict[str, Any]] = field(default_factory=list)

    @property
    def rounds_remaining(self) -> int:
        """Rounds still to execute for this run."""
        return max(0, self.max_rounds - self.round)


def is_resumable(checkpoint: AgentGroupTaskCheckpoint | None) -> bool:
    """Report whether a checkpoint represents unfinished work.

    Args:
        checkpoint: The checkpoint to inspect, or None.

    Returns:
        True when the checkpoint is in a state worth resuming from.
    """
    return bool(
        checkpoint is not None
        and checkpoint.status in RESUMABLE_CHECKPOINT_STATUSES
    )


async def save_checkpoint(
    task_id: str,
    group_id: str,
    current_round: int,
    max_rounds: int,
    current_artifact: str,
    all_issues: list[dict[str, Any]],
    status: str = "running",
) -> None:
    """Save execution checkpoint for resume capability.

    Args:
        task_id: The task ID.
        group_id: The group ID.
        current_round: The current execution round.
        max_rounds: The maximum number of rounds.
        current_artifact: The current output artifact.
        all_issues: List of issues identified so far.
        status: State the task was in when the checkpoint was taken. Recording
            a terminal state here keeps a finished task off the resume path;
            the default keeps a mid-run checkpoint resumable.
    """
    async with async_session() as db:
        task = await db.get(AgentGroupTask, task_id)
        checkpoint = AgentGroupTaskCheckpoint(
            group_id=group_id,
            task_id=task_id,
            status=status,
            current_round=current_round,
            max_rounds=max_rounds,
            current_artifact=current_artifact,
            all_issues=all_issues,
            task_description=task.description if task else "",
            output_schema=task.output_schema if task else {},
        )
        db.add(checkpoint)
        await db.commit()


async def load_latest_checkpoint(task_id: str) -> AgentGroupTaskCheckpoint | None:
    """Load the latest checkpoint for a task.

    ``created_at`` has one-second resolution, so checkpoints written inside the
    same second tie; ``current_round`` breaks the tie because a task's rounds
    only ever move forward.

    Args:
        task_id: The task ID to load checkpoint for.

    Returns:
        The latest checkpoint or None if not found.
    """
    async with async_session() as db:
        result = (
            await db.execute(
                select(AgentGroupTaskCheckpoint)
                .where(AgentGroupTaskCheckpoint.task_id == task_id)
                .order_by(
                    AgentGroupTaskCheckpoint.created_at.desc(),
                    AgentGroupTaskCheckpoint.current_round.desc(),
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        return result


async def claim_checkpoint_for_resume(
    checkpoint: AgentGroupTaskCheckpoint,
    lease_seconds: int = RESUME_LEASE_SECONDS,
) -> bool:
    """Take exclusive ownership of a checkpoint before resuming from it.

    The claim is a compare-and-set: the ``UPDATE`` only matches while the row
    still carries the status and round the caller observed, so two resumers
    racing on the same checkpoint cannot both win. The winning claim parks the
    row in ``resuming`` with a lease timestamp, which makes a second attempt
    fail while the first is still alive and makes a crashed resumer reclaimable
    after the lease expires.

    Args:
        checkpoint: The checkpoint observed by the caller.
        lease_seconds: How long the claim stays valid.

    Returns:
        True when this caller claimed the checkpoint, False when another
        resumer already owns it or the row moved on.
    """
    if checkpoint.id is None:
        return False

    async with async_session() as db:
        row = await db.get(AgentGroupTaskCheckpoint, checkpoint.id)
        if row is None or row.status not in RESUMABLE_CHECKPOINT_STATUSES:
            return False
        if row.current_round != checkpoint.current_round:
            return False
        if _lease_is_live(row.context_data, lease_seconds):
            return False

        now = datetime.now(UTC)
        context_data = {**(row.context_data or {}), _LEASE_KEY: now.isoformat()}
        result = await db.execute(
            update(AgentGroupTaskCheckpoint)
            .where(
                AgentGroupTaskCheckpoint.id == row.id,
                AgentGroupTaskCheckpoint.status == row.status,
                AgentGroupTaskCheckpoint.current_round == row.current_round,
            )
            .values(status="resuming", context_data=context_data)
        )
        await db.commit()
        claimed = result.rowcount == 1

    if not claimed:
        logger.info("checkpoint_resume_lost", checkpoint_id=checkpoint.id)
    return claimed


def _lease_is_live(context_data: dict[str, Any] | None, lease_seconds: int) -> bool:
    """Report whether a live resume lease is recorded in the checkpoint context."""
    started_at = (context_data or {}).get(_LEASE_KEY)
    if not started_at:
        return False
    try:
        started = datetime.fromisoformat(str(started_at))
    except ValueError:
        return False
    if started.tzinfo is None:
        started = started.replace(tzinfo=UTC)
    return datetime.now(UTC) - started < timedelta(seconds=lease_seconds)


async def resume_from_checkpoint(
    task: Any,
    checkpoint: AgentGroupTaskCheckpoint,
) -> ResumeState | None:
    """Claim a checkpoint and restore the task row to its checkpointed state.

    The restored state is returned so the caller can hand it straight to the
    sequencer and continue with the next round. Returns None when the
    checkpoint was already claimed by another resumer, which makes repeated
    resume attempts no-ops instead of double-charging a round.

    Args:
        task: The task entity to resume.
        checkpoint: The checkpoint to resume from.

    Returns:
        The state the sequencer must continue from, or None if the checkpoint
        could not be claimed.
    """
    if not await claim_checkpoint_for_resume(checkpoint):
        logger.info(
            "checkpoint_resume_skipped",
            task_id=task.id,
            checkpoint_id=checkpoint.id,
        )
        return None

    artifact = checkpoint.current_artifact or ""
    issues = [issue for issue in (checkpoint.all_issues or []) if isinstance(issue, dict)]

    async with async_session() as db:
        t = await db.get(AgentGroupTask, task.id)
        if t:
            t.status = "running"
            t.final_output = artifact
            t.current_round = checkpoint.current_round
            await db.commit()

    await group_ws_hub.broadcast(task.group_id, {
        "type": "checkpoint_restored",
        "data": {"task_id": task.id, "checkpoint_id": checkpoint.id, "round": checkpoint.current_round},
    })
    await group_ws_hub.broadcast(task.group_id, {
        "type": "task_partial",
        "data": {"task_id": task.id, "final_output": artifact, "rounds": checkpoint.current_round},
    })

    return ResumeState(
        checkpoint_id=checkpoint.id,
        round=checkpoint.current_round,
        max_rounds=checkpoint.max_rounds,
        worker_output=artifact,
        all_issues=issues,
    )
