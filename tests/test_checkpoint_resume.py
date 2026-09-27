"""Checkpoint resume regression tests (audit item P2-18).

``save_checkpoint`` hardcoded ``status="running"``, so a restart always hit the
resume branch in ``GroupCollaborationEngine.run_task``; that branch wrote the
checkpoint back and returned without re-entering ``run_sequential_process``, so
a checkpointed task never ran another LLM call and never finished.

These tests run a real multi-round task against the real sequencer with the
agent calls faked, crash it mid-way, restart it, and assert the remaining
rounds ran and the final output is complete and not duplicated.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
import pytest_asyncio

from app.core.collaboration import checkpoint as checkpoint_module
from app.core.collaboration import sequential as sequential_module
from app.core.collaboration.base import GroupCollaborationEngine
from app.core.collaboration.checkpoint import (
    ResumeState,
    claim_checkpoint_for_resume,
    is_resumable,
    load_latest_checkpoint,
    resume_from_checkpoint,
    save_checkpoint,
)
from app.storage import async_session
from app.storage.models_groups import AgentGroup, AgentGroupMember, AgentGroupTask, AgentGroupTaskCheckpoint

GROUP_ID = "ckpt-group"
TASK_ID = "ckpt-task"
WORKER_ID = "ckpt-worker"
REVIEWER_ID = "ckpt-reviewer"
MAX_ROUNDS = 3

#: Reviewer verdict that fails the round: it contains no acceptance keyword and
#: one line that parses as an issue.
REJECT_REVIEW = "rejected\n- issue: missing detail"
ACCEPT_REVIEW = "通过"


class _WorkerStub:
    """Stands in for ``run_agent_with_retry`` and can fail a chosen round."""

    def __init__(self, crash_on_call: int | None = None) -> None:
        self.crash_on_call = crash_on_call
        self.calls: list[str] = []
        self.prompts: list[str] = []

    async def __call__(self, **kwargs: Any) -> tuple[str, int]:
        index = len(self.prompts) + 1
        self.prompts.append(kwargs["user_message"])
        if self.crash_on_call is not None and index == self.crash_on_call:
            self.calls.append(f"crash-{index}")
            raise RuntimeError("worker crashed mid-task")
        draft = f"draft-{index}"
        self.calls.append(draft)
        return draft, 10


class _ReviewerStub:
    """Stands in for ``run_agent_simple``; rejects the first ``fail_first`` turns."""

    def __init__(self, fail_first: int = 1) -> None:
        self.fail_first = fail_first
        self.calls = 0

    async def __call__(self, **kwargs: Any) -> tuple[str, int]:
        self.calls += 1
        if self.calls <= self.fail_first:
            return REJECT_REVIEW, 0
        return ACCEPT_REVIEW, 0


@pytest_asyncio.fixture
async def task_fixture(monkeypatch: pytest.MonkeyPatch):
    """Create a group with a worker, a reviewer and a 3-round task.

    Yields a dict with the fakes, the recorded broadcasts and the engine. Row
    cleanup is handled by the session-wide ``cleanup_db`` fixture.
    """
    async with async_session() as db:
        db.add(AgentGroup(id=GROUP_ID, name="ckpt", user_id="default-user", process_type="sequential"))
        db.add(
            AgentGroupMember(
                id=WORKER_ID,
                group_id=GROUP_ID,
                agent_id="worker-agent",
                role="worker",
                model_provider="ollama",
                model_id="local",
                is_worker=True,
            )
        )
        db.add(
            AgentGroupMember(
                id=REVIEWER_ID,
                group_id=GROUP_ID,
                agent_id="reviewer-agent",
                role="reviewer",
                model_provider="ollama",
                model_id="local",
            )
        )
        db.add(
            AgentGroupTask(
                id=TASK_ID,
                group_id=GROUP_ID,
                description="write a report",
                status="pending",
                worker_id=WORKER_ID,
                reviewer_ids=[REVIEWER_ID],
                max_rounds=MAX_ROUNDS,
                guardrails=[],
                output_schema={},
            )
        )
        await db.commit()

    worker = _WorkerStub()
    reviewer = _ReviewerStub(fail_first=MAX_ROUNDS - 1)
    monkeypatch.setattr(sequential_module, "run_agent_with_retry", worker)
    monkeypatch.setattr("app.core.collaboration.agent_runner.run_agent_simple", reviewer)

    broadcasts: list[dict] = []

    async def _record(group_id: str, message: dict) -> None:
        broadcasts.append(message)

    monkeypatch.setattr(checkpoint_module.group_ws_hub, "broadcast", _record)
    monkeypatch.setattr(sequential_module.group_ws_hub, "broadcast", _record)

    engine = GroupCollaborationEngine(model_registry=object(), tool_registry=object())
    yield {"worker": worker, "reviewer": reviewer, "broadcasts": broadcasts, "engine": engine}


async def _task_row() -> AgentGroupTask | None:
    async with async_session() as db:
        return await db.get(AgentGroupTask, TASK_ID)


async def _latest_checkpoint() -> AgentGroupTaskCheckpoint | None:
    return await load_latest_checkpoint(TASK_ID)


class TestCheckpointRecordsReality:
    """``save_checkpoint`` must not claim every snapshot is mid-run."""

    async def test_completed_run_leaves_a_non_resumable_checkpoint(self, task_fixture) -> None:
        await task_fixture["engine"].run_task(TASK_ID)

        row = await _task_row()
        assert row.status == "completed"
        assert row.final_output == "draft-3"

        latest = await _latest_checkpoint()
        assert latest is not None
        assert latest.status == "completed"
        assert is_resumable(latest) is False

    async def test_mid_run_checkpoint_stays_resumable(self, task_fixture) -> None:
        task_fixture["worker"].crash_on_call = 2
        await task_fixture["engine"].run_task(TASK_ID)

        latest = await _latest_checkpoint()
        assert latest is not None
        assert latest.status == "running"
        assert latest.current_round == 1
        assert is_resumable(latest) is True

    async def test_explicit_status_is_recorded(self, task_fixture) -> None:
        await save_checkpoint(TASK_ID, GROUP_ID, 2, MAX_ROUNDS, "artifact", [], status="paused")
        latest = await _latest_checkpoint()
        assert latest.status == "paused"
        assert is_resumable(latest) is True


class TestResumeContinuesTheLoop:
    """A restart must run the rounds the checkpoint left behind."""

    async def test_remaining_rounds_run_after_restart(self, task_fixture) -> None:
        worker = task_fixture["worker"]
        engine = task_fixture["engine"]
        worker.crash_on_call = 2

        await engine.run_task(TASK_ID)
        crashed = await _task_row()
        assert crashed.status == "running"
        assert crashed.current_round == 2
        assert worker.calls == ["draft-1", "crash-2"]

        checkpoint = await _latest_checkpoint()
        assert checkpoint.current_round == 1
        assert checkpoint.current_artifact == "draft-1"

        await engine.run_task(TASK_ID)

        # Exactly the two remaining rounds ran: no replay of round 1.
        assert worker.calls == ["draft-1", "crash-2", "draft-3", "draft-4"]
        assert worker.prompts[1].startswith("Task: write a report")
        assert "Previous output:\ndraft-1" in worker.prompts[2], "resume must restore the checkpointed output"
        assert "Issues to fix:" in worker.prompts[2], "resume must restore the outstanding issues"
        assert "Previous output:\ndraft-3" in worker.prompts[3]

        final = await _task_row()
        assert final.status == "completed"
        assert final.current_round == 3
        assert final.final_output == "draft-4"
        assert final.final_output.count("draft-4") == 1
        assert "draft-1" not in final.final_output

        final_checkpoint = await _latest_checkpoint()
        assert final_checkpoint.status == "completed"
        assert final_checkpoint.current_round == 3

    async def test_resume_runs_to_the_round_budget(self, task_fixture) -> None:
        worker = task_fixture["worker"]
        worker.crash_on_call = 2

        await task_fixture["engine"].run_task(TASK_ID)
        await task_fixture["engine"].run_task(TASK_ID)

        final = await _task_row()
        assert final.status == "completed"
        assert final.current_round == 3
        assert len(worker.calls) == 4
        assert final.final_output == "draft-4"

    async def test_resume_broadcasts_restore_and_partial(self, task_fixture) -> None:
        broadcasts = task_fixture["broadcasts"]
        task_fixture["worker"].crash_on_call = 2

        await task_fixture["engine"].run_task(TASK_ID)
        broadcasts.clear()
        await task_fixture["engine"].run_task(TASK_ID)

        types = [message["type"] for message in broadcasts]
        assert "checkpoint_restored" in types
        assert "task_partial" in types
        assert types.index("checkpoint_restored") < types.index("worker_start")


class TestResumeIsIdempotent:
    """Resuming twice must not double-charge or double-append."""

    async def test_second_run_task_on_a_finished_task_does_nothing(self, task_fixture) -> None:
        worker = task_fixture["worker"]
        engine = task_fixture["engine"]
        await engine.run_task(TASK_ID)
        finished = list(worker.calls)
        assert finished == ["draft-1", "draft-2", "draft-3"]

        await engine.run_task(TASK_ID)
        await engine.run_task(TASK_ID)
        assert worker.calls == finished, "a completed task must not be executed again"

    async def test_a_claimed_checkpoint_cannot_be_claimed_twice(self, task_fixture) -> None:
        task_fixture["worker"].crash_on_call = 2
        await task_fixture["engine"].run_task(TASK_ID)

        checkpoint = await _latest_checkpoint()
        task = await _task_row()
        first = await resume_from_checkpoint(task, checkpoint)
        second = await resume_from_checkpoint(task, checkpoint)

        assert isinstance(first, ResumeState)
        assert first.round == 1
        assert first.worker_output == "draft-1"
        assert second is None

    async def test_a_live_lease_blocks_a_concurrent_resumer(self, task_fixture) -> None:
        task_fixture["worker"].crash_on_call = 2
        engine = task_fixture["engine"]
        await engine.run_task(TASK_ID)

        checkpoint = await _latest_checkpoint()
        assert await claim_checkpoint_for_resume(checkpoint) is True

        before = len(task_fixture["worker"].calls)
        await engine.run_task(TASK_ID)
        assert len(task_fixture["worker"].calls) == before, "the live resumer already owns this checkpoint"

    async def test_expired_lease_allows_recovery_after_a_crash(self, task_fixture) -> None:
        task_fixture["worker"].crash_on_call = 2
        await task_fixture["engine"].run_task(TASK_ID)

        checkpoint = await _latest_checkpoint()
        assert await claim_checkpoint_for_resume(checkpoint) is True

        stale = (datetime.now(UTC) - timedelta(days=1)).isoformat()
        async with async_session() as db:
            row = await db.get(AgentGroupTaskCheckpoint, checkpoint.id)
            row.context_data = {"resume_started_at": stale}
            await db.commit()

        assert await claim_checkpoint_for_resume(checkpoint) is True

    async def test_resume_state_rounds_remaining(self) -> None:
        state = ResumeState(checkpoint_id="c", round=2, max_rounds=5)
        assert state.rounds_remaining == 3
        assert state.all_issues == []

    async def test_claim_is_rejected_for_a_completed_checkpoint(self, task_fixture) -> None:
        await task_fixture["engine"].run_task(TASK_ID)
        checkpoint = await _latest_checkpoint()
        assert await claim_checkpoint_for_resume(checkpoint) is False


class TestResumeStateRestore:
    """The restored task row must match the checkpoint."""

    async def test_task_row_is_restored_from_checkpoint(self, task_fixture) -> None:
        task_fixture["worker"].crash_on_call = 2
        await task_fixture["engine"].run_task(TASK_ID)

        checkpoint = await _latest_checkpoint()
        task = await _task_row()
        resumed = await resume_from_checkpoint(task, checkpoint)

        assert resumed is not None
        assert resumed.checkpoint_id == checkpoint.id
        assert resumed.max_rounds == MAX_ROUNDS

        restored = await _task_row()
        assert restored.status == "running"
        assert restored.current_round == 1
        assert restored.final_output == "draft-1"

    async def test_resume_carries_outstanding_issues(self, task_fixture) -> None:
        task_fixture["worker"].crash_on_call = 2
        await task_fixture["engine"].run_task(TASK_ID)

        checkpoint = await _latest_checkpoint()
        assert checkpoint.all_issues, "the rejected review must have been checkpointed"
        task = await _task_row()
        resumed = await resume_from_checkpoint(task, checkpoint)

        assert resumed is not None
        assert resumed.all_issues == checkpoint.all_issues
        assert resumed.round == 1
        assert resumed.rounds_remaining == MAX_ROUNDS - 1
