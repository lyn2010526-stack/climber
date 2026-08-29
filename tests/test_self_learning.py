"""Tests for closed-loop self-learning L1/L2/L3."""

from __future__ import annotations

import pytest

from app.core.self_learning import (
    BackgroundDistiller,
    OperationRecord,
    RealtimeFixer,
    SkillSteward,
)
from app.core.skill_store import SkillMetadata, SkillStore


def test_l1_realtime_fix_patches_skill(tmp_path):
    store = SkillStore(base_dir=str(tmp_path / "skills"))
    store.create("fixme", SkillMetadata(name="fixme", description="fix"), "click( 100, 200 )")
    fixer = RealtimeFixer(store, max_retries=2)
    fixed, _new = fixer.fix("fixme", "coordinate error: invalid position", "click( 100, 200 )")
    # The fix should normalize coordinate spacing
    assert fixed


def test_l1_fix_history_and_rollback(tmp_path):
    store = SkillStore(base_dir=str(tmp_path / "skills_l1"))
    store.create("fixme", SkillMetadata(name="fixme"), "click( 100, 200 )")
    fixer = RealtimeFixer(store)
    fixer.fix("fixme", "coordinate error: out of bounds", "click( 100, 200 )")
    assert len(fixer.history()) == 1
    assert fixer.rollback("fixme") is True
    skill = store.get("fixme")
    assert skill.load_instruction() == "click( 100, 200 )"


@pytest.mark.asyncio
async def test_l2_distill_creates_skill(tmp_path):
    store = SkillStore(base_dir=str(tmp_path / "skills_l2"))
    distiller = BackgroundDistiller(store, min_operations=1)
    ops = [
        OperationRecord(operation="open app"),
        OperationRecord(operation="click button"),
        OperationRecord(operation="verify result"),
    ]
    result = await distiller.distill("test flow", ops, app_list=["com.test"])
    assert result.created
    assert store.get(result.skill_id) is not None


@pytest.mark.asyncio
async def test_l2_distill_skips_few_ops(tmp_path):
    store = SkillStore(base_dir=str(tmp_path / "skills_l2b"))
    distiller = BackgroundDistiller(store, min_operations=10)
    ops = [OperationRecord(operation="click") for _ in range(3)]
    result = await distiller.distill("tiny", ops)
    assert not result.created


def test_l3_steward_merges_duplicates(tmp_path):
    store = SkillStore(base_dir=str(tmp_path / "skills_l3"))
    store.create("dup_a", SkillMetadata(name="duplicate skill", description="do foo"), "step1")
    store.create("dup_b", SkillMetadata(name="duplicate skill", description="do foo too"), "step1")
    steward = SkillSteward(store, threshold_skills=1, archive_after_days=9999)
    report = steward.run()
    merge_actions = [a for a in report.actions if a.action == "merged"]
    assert len(merge_actions) >= 1


def test_l3_steward_optimizes_descriptions(tmp_path):
    store = SkillStore(base_dir=str(tmp_path / "skills_l3b"))
    store.create("sk", SkillMetadata(name="sk", description="Skill: do something"), "step1")
    steward = SkillSteward(store, threshold_skills=1, archive_after_days=9999)
    report = steward.run()
    optimize_actions = [a for a in report.actions if a.action == "optimized"]
    assert len(optimize_actions) >= 1
    skill = store.get("sk")
    assert not skill.metadata.description.startswith("Skill: ")


def test_l3_steward_report_format(tmp_path):
    store = SkillStore(base_dir=str(tmp_path / "skills_l3c"))
    store.create("sk", SkillMetadata(name="sk"), "step1")
    steward = SkillSteward(store, threshold_skills=1)
    report = steward.run()
    assert report.skills_before >= 1
    assert report.triggered_at > 0
    assert isinstance(report.to_dict(), dict)
