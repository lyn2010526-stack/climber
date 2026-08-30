"""Contract tests for structured artifacts in group collaboration."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.core.artifacts import (
    Artifact,
    ArtifactStage,
    ArtifactStatus,
    ArtifactType,
    GateKind,
    HandoffAudit,
    StageGateError,
)
from app.core.group_collaboration import get_group_collaboration_engine
from app.storage import async_session
from app.storage.models_groups import AgentGroup, AgentGroupMember, AgentGroupTask


def test_artifact_round_trips_json_and_revision_records_lineage() -> None:
    draft = Artifact.create(
        artifact_type=ArtifactType.RESULT,
        stage=ArtifactStage.DRAFT,
        content={"summary": "first", "scores": [1, 2]},
    )

    restored = Artifact.from_dict(json.loads(json.dumps(draft.to_dict())))
    revised = restored.revise(content={"summary": "second", "scores": [3]})

    assert restored == draft
    assert revised.version == 2
    assert revised.lineage[-1].artifact_id == draft.artifact_id
    assert revised.lineage[-1].version == 1
    assert revised.content == {"summary": "second", "scores": [3]}
    assert draft.content == {"summary": "first", "scores": [1, 2]}


def test_schema_reviewer_and_human_gates_control_stage_transition() -> None:
    artifact = Artifact.create(
        artifact_type=ArtifactType.RESULT,
        stage=ArtifactStage.REVIEW,
        content={"answer": 42},
        required_gates=(GateKind.SCHEMA, GateKind.REVIEWER, GateKind.HUMAN),
    )

    artifact = artifact.record_gate(GateKind.SCHEMA, approved=True, actor="json-schema")
    artifact = artifact.record_gate(GateKind.REVIEWER, approved=False, actor="reviewer-1", reason="needs evidence")
    assert artifact.status is ArtifactStatus.BLOCKED
    with pytest.raises(StageGateError, match="reviewer"):
        artifact.advance(ArtifactStage.FINAL)

    artifact = artifact.record_gate(GateKind.REVIEWER, approved=True, actor="reviewer-1")
    artifact = artifact.record_gate(GateKind.HUMAN, approved=True, actor="human-1")
    final = artifact.advance(ArtifactStage.FINAL)

    assert final.status is ArtifactStatus.APPROVED
    assert final.stage is ArtifactStage.FINAL


def test_checkpoint_payload_preserves_artifact_workflow_status() -> None:
    artifact = Artifact.create(
        artifact_type=ArtifactType.RESULT,
        stage=ArtifactStage.REVIEW,
        content={"answer": 42},
        required_gates=(GateKind.SCHEMA,),
    ).record_gate(GateKind.SCHEMA, approved=True, actor="json-schema")

    restored = Artifact.from_checkpoint(artifact.to_checkpoint())

    assert restored == artifact
    assert restored is not None
    assert restored.status is ArtifactStatus.APPROVED
    assert Artifact.from_checkpoint("legacy plain-text output") is None


def test_handoff_audit_pins_an_approved_artifact_version() -> None:
    artifact = Artifact.create(
        artifact_type=ArtifactType.RESULT,
        stage=ArtifactStage.REVIEW,
        content={"answer": 42},
        required_gates=(GateKind.SCHEMA,),
    ).record_gate(GateKind.SCHEMA, approved=True, actor="json-schema")
    audit = HandoffAudit.capture(artifact, from_agent="member-1", to_agent="member-2", reason="specialist review")
    revised = artifact.revise(content={"answer": 43})

    assert audit.artifact_id == artifact.artifact_id
    assert audit.artifact_version == 1
    assert audit.content == {"answer": 42}
    assert audit.content_digest != HandoffAudit.content_hash(revised.content)


def test_handoff_rejects_artifact_that_has_not_passed_required_gates() -> None:
    artifact = Artifact.create(
        artifact_type=ArtifactType.RESULT,
        stage=ArtifactStage.REVIEW,
        content={"answer": 42},
        required_gates=(GateKind.HUMAN,),
    )

    with pytest.raises(StageGateError, match="human"):
        HandoffAudit.capture(artifact, from_agent="member-1", to_agent="member-2")


@pytest.mark.asyncio
async def test_group_handoff_captures_source_before_update_and_broadcasts_fixed_artifact() -> None:
    async with async_session() as db:
        group = AgentGroup(name="artifact-handoff", user_id="default-user")
        db.add(group)
        await db.commit()
        await db.refresh(group)
        source = AgentGroupMember(group_id=group.id, agent_id="agent-1", role="worker")
        target = AgentGroupMember(group_id=group.id, agent_id="agent-2", role="worker")
        db.add_all([source, target])
        await db.commit()
        await db.refresh(source)
        await db.refresh(target)
        task = AgentGroupTask(group_id=group.id, description="handoff task", worker_id=source.id)
        db.add(task)
        await db.commit()
        await db.refresh(task)
        task_id = task.id
        source_id = source.id
        target_id = target.id

    artifact = Artifact.create(
        artifact_type=ArtifactType.RESULT,
        stage=ArtifactStage.REVIEW,
        content={"answer": 42},
        required_gates=(GateKind.SCHEMA,),
    ).record_gate(GateKind.SCHEMA, approved=True, actor="json-schema")
    engine = get_group_collaboration_engine()
    with patch("app.core.group_collaboration.group_ws_hub.broadcast", new_callable=AsyncMock) as broadcast:
        result = await engine.handoff_task(task_id, "agent-2", "specialist", artifact=artifact)

    event = broadcast.await_args.args[1]
    assert event["data"]["from_agent"] == source_id
    assert event["data"]["to_agent"] == target_id
    assert event["data"]["artifact"]["artifact_version"] == 1
    assert result["handoff_audit"]["artifact_id"] == artifact.artifact_id

    async with async_session() as db:
        persisted = await db.get(AgentGroupTask, task_id)
        assert persisted is not None
        assert persisted.worker_id == target_id


@pytest.mark.asyncio
async def test_group_handoff_rejects_target_from_another_group() -> None:
    async with async_session() as db:
        source_group = AgentGroup(name="source-group", user_id="default-user")
        target_group = AgentGroup(name="target-group", user_id="default-user")
        db.add_all([source_group, target_group])
        await db.commit()
        await db.refresh(source_group)
        await db.refresh(target_group)
        source = AgentGroupMember(group_id=source_group.id, agent_id="source", role="worker")
        target = AgentGroupMember(group_id=target_group.id, agent_id="target", role="worker")
        db.add_all([source, target])
        await db.commit()
        await db.refresh(source)
        task = AgentGroupTask(group_id=source_group.id, description="handoff task", worker_id=source.id)
        db.add(task)
        await db.commit()
        await db.refresh(task)

    with pytest.raises(Exception, match="Target agent not found"):
        await get_group_collaboration_engine().handoff_task(task.id, "target")


@pytest.mark.asyncio
async def test_final_artifact_checkpoint_restores_task_as_completed() -> None:
    async with async_session() as db:
        group = AgentGroup(name="checkpoint-group", user_id="default-user")
        db.add(group)
        await db.commit()
        await db.refresh(group)
        task = AgentGroupTask(
            group_id=group.id,
            description="structured task",
            status="running",
            output_schema={"type": "object"},
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)

    artifact = Artifact.create(
        artifact_type=ArtifactType.RESULT,
        stage=ArtifactStage.REVIEW,
        content={"answer": 42},
        required_gates=(GateKind.SCHEMA,),
    ).record_gate(GateKind.SCHEMA, approved=True, actor="json-schema").advance(ArtifactStage.FINAL)
    engine = get_group_collaboration_engine()
    assert await engine._save_checkpoint(task.id, group.id, 1, 1, artifact, []) is True
    checkpoint = await engine._load_latest_checkpoint(task.id)

    assert checkpoint is not None
    assert checkpoint.status == "completed"
    restored = await engine._resume_from_checkpoint(task, checkpoint)
    assert restored is not None
    assert restored.status == "completed"
    assert restored.structured_output == {"answer": 42}


@pytest.mark.asyncio
async def test_reviewer_exception_blocks_plain_text_completion() -> None:
    async with async_session() as db:
        group = AgentGroup(name="reviewer-failure-group", user_id="default-user")
        db.add(group)
        await db.commit()
        await db.refresh(group)
        worker = AgentGroupMember(
            group_id=group.id,
            agent_id="worker",
            role="worker",
            model_provider="openai",
        )
        reviewer = AgentGroupMember(
            group_id=group.id,
            agent_id="reviewer",
            role="reviewer",
            model_provider="openai",
        )
        db.add_all([worker, reviewer])
        await db.commit()
        await db.refresh(worker)
        await db.refresh(reviewer)
        task = AgentGroupTask(
            group_id=group.id,
            description="plain text review",
            worker_id=worker.id,
            reviewer_ids=[reviewer.id],
            max_rounds=1,
            status="running",
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)
        task_id = task.id

    engine = get_group_collaboration_engine()
    with (
        patch.object(engine, "_build_context_from_dependencies", new_callable=AsyncMock, return_value=[]),
        patch.object(engine, "_inject_memory", new_callable=AsyncMock, return_value=[]),
        patch.object(engine, "_run_agent_with_retry", new_callable=AsyncMock, return_value=("plain result", 1)),
        patch.object(engine, "_run_agent_simple", new_callable=AsyncMock, side_effect=RuntimeError("review unavailable")),
        patch.object(engine, "_run_guardrails", new_callable=AsyncMock, return_value=(True, [])),
        patch.object(engine, "_invoke_step_callback", new_callable=AsyncMock),
        patch("app.core.group_collaboration.group_ws_hub.broadcast", new_callable=AsyncMock),
    ):
        await engine._run_sequential_process(task, worker, [reviewer], group)

    async with async_session() as db:
        persisted = await db.get(AgentGroupTask, task_id)
        assert persisted is not None
        assert persisted.status == "partial"
    checkpoint = await engine._load_latest_checkpoint(task_id)
    assert checkpoint is not None
    assert "Reviewer stage gate failed" in checkpoint.all_issues[0]["description"]


@pytest.mark.parametrize(
    ("review_output", "expected"),
    [
        ("通过", True),
        ("1. Approved", True),
        ("不通过：缺少测试证据", False),
        ("Not approved because tests are missing", False),
        ("This is unacceptable", False),
        ("Did not pass review", False),
    ],
)
def test_reviewer_gate_rejects_negative_verdicts(review_output: str, expected: bool) -> None:
    engine = get_group_collaboration_engine()

    assert engine._review_passed(review_output) is expected


@pytest.mark.asyncio
async def test_plain_text_success_checkpoint_is_completed() -> None:
    async with async_session() as db:
        group = AgentGroup(name="plain-checkpoint-group", user_id="default-user")
        db.add(group)
        await db.commit()
        await db.refresh(group)
        worker = AgentGroupMember(
            group_id=group.id,
            agent_id="worker",
            role="worker",
            model_provider="openai",
        )
        db.add(worker)
        await db.commit()
        await db.refresh(worker)
        task = AgentGroupTask(
            group_id=group.id,
            description="plain checkpoint",
            worker_id=worker.id,
            max_rounds=1,
            status="running",
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)
        task_id = task.id

    engine = get_group_collaboration_engine()
    with (
        patch.object(engine, "_build_context_from_dependencies", new_callable=AsyncMock, return_value=[]),
        patch.object(engine, "_inject_memory", new_callable=AsyncMock, return_value=[]),
        patch.object(engine, "_run_agent_with_retry", new_callable=AsyncMock, return_value=("plain result", 1)),
        patch.object(engine, "_run_guardrails", new_callable=AsyncMock, return_value=(True, [])),
        patch.object(engine, "_invoke_step_callback", new_callable=AsyncMock),
        patch.object(engine, "_store_memory", new_callable=AsyncMock),
        patch.object(engine, "_invoke_task_callback", new_callable=AsyncMock),
        patch("app.core.group_collaboration.group_ws_hub.broadcast", new_callable=AsyncMock),
    ):
        await engine._run_sequential_process(task, worker, [], group)

    async with async_session() as db:
        persisted = await db.get(AgentGroupTask, task_id)
        assert persisted is not None
        assert persisted.status == "completed"
    checkpoint = await engine._load_latest_checkpoint(task_id)
    assert checkpoint is not None
    assert checkpoint.status == "completed"
