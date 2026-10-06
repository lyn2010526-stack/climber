"""Configurable subtask concurrency: default 3, hard ceiling 18."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import patch

import pytest

from app.config import (
    DEFAULT_MAX_CONCURRENT_SUBTASKS,
    MAX_CONCURRENT_SUBTASKS_CEILING,
    Settings,
    settings,
)
from app.core.collaboration.base import GroupCollaborationEngine
from app.core.engine.subagent import SubagentManager, SubagentSpec, SubagentUsage
from app.core.task_worker import TaskManager, task_manager

YIELDS_PER_TASK = 10


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MAX_CONCURRENT_SUBTASKS", raising=False)


def _make_settings(**overrides: Any) -> Settings:
    return Settings(_env_file=None, **overrides)


def _group_engine() -> GroupCollaborationEngine:
    return GroupCollaborationEngine(model_registry=object(), tool_registry=object())


def _group_engine_with(max_concurrent_tasks: int) -> GroupCollaborationEngine:
    return GroupCollaborationEngine(
        model_registry=object(),
        tool_registry=object(),
        max_concurrent_tasks=max_concurrent_tasks,
    )


async def _measure_task_manager(manager: TaskManager, total: int) -> int:
    counters = {"current": 0, "peak": 0}

    async def fake_task() -> None:
        async with manager.slot():
            counters["current"] += 1
            counters["peak"] = max(counters["peak"], counters["current"])
            for _ in range(YIELDS_PER_TASK):
                await asyncio.sleep(0)
            counters["current"] -= 1

    await asyncio.gather(*(fake_task() for _ in range(total)))
    return counters["peak"]


async def _measure_subagent_manager(manager: SubagentManager, total: int) -> int:
    counters = {"current": 0, "peak": 0}

    async def runner(_spec: SubagentSpec) -> tuple[str, SubagentUsage]:
        counters["current"] += 1
        counters["peak"] = max(counters["peak"], counters["current"])
        for _ in range(YIELDS_PER_TASK):
            await asyncio.sleep(0)
        counters["current"] -= 1
        return "done", SubagentUsage()

    await asyncio.gather(
        *(
            manager.spawn(SubagentSpec(description=f"task-{index}"), runner)
            for index in range(total)
        )
    )
    return counters["peak"]


def test_default_concurrency_is_three() -> None:
    assert DEFAULT_MAX_CONCURRENT_SUBTASKS == 3
    assert _make_settings().max_concurrent_subtasks == 3
    assert settings.max_concurrent_subtasks == 3


def test_hard_ceiling_is_eighteen() -> None:
    assert MAX_CONCURRENT_SUBTASKS_CEILING == 18


@pytest.mark.parametrize("configured", [1, 2, 3, 9, 17, 18])
def test_values_inside_range_are_preserved(configured: int) -> None:
    assert _make_settings(max_concurrent_subtasks=configured).max_concurrent_subtasks == configured


@pytest.mark.parametrize("configured", [19, 20, 100, 10_000])
def test_values_above_ceiling_are_clamped(configured: int) -> None:
    with patch("app.config.logger") as log:
        resolved = _make_settings(max_concurrent_subtasks=configured).max_concurrent_subtasks
    assert resolved == 18
    log.warning.assert_called_once()
    assert log.warning.call_args.kwargs["applied"] == 18
    assert log.warning.call_args.kwargs["requested"] == configured
    assert log.warning.call_args.kwargs["ceiling"] == 18


@pytest.mark.parametrize("configured", [0, -1, -18])
def test_non_positive_values_are_clamped_to_one(configured: int) -> None:
    with patch("app.config.logger") as log:
        resolved = _make_settings(max_concurrent_subtasks=configured).max_concurrent_subtasks
    assert resolved == 1
    log.warning.assert_called_once()
    assert log.warning.call_args.kwargs["applied"] == 1
    assert log.warning.call_args.kwargs["requested"] == configured


def test_in_range_value_logs_no_warning() -> None:
    with patch("app.config.logger") as log:
        assert _make_settings(max_concurrent_subtasks=3).max_concurrent_subtasks == 3
    log.warning.assert_not_called()


def test_task_manager_defaults_to_configured_value() -> None:
    assert TaskManager().max_workers == settings.max_concurrent_subtasks
    assert task_manager.max_workers == settings.max_concurrent_subtasks


@pytest.mark.parametrize("explicit", [1, 5, 18])
def test_task_manager_explicit_override_wins(explicit: int) -> None:
    assert TaskManager(max_workers=explicit).max_workers == explicit


def test_group_engine_defaults_to_configured_value() -> None:
    assert _group_engine()._max_concurrent == settings.max_concurrent_subtasks
    assert _group_engine()._task_semaphore._value == settings.max_concurrent_subtasks


@pytest.mark.parametrize("explicit", [1, 5, 18])
def test_group_engine_explicit_override_wins(explicit: int) -> None:
    assert _group_engine_with(explicit)._max_concurrent == explicit


def test_subagent_manager_defaults_to_configured_value() -> None:
    assert SubagentManager().get_stats()["concurrency_limit"] == settings.max_concurrent_subtasks


@pytest.mark.parametrize("explicit", [1, 5, 18])
def test_subagent_manager_explicit_override_wins(explicit: int) -> None:
    assert SubagentManager(concurrency_limit=explicit).get_stats()["concurrency_limit"] == explicit


def test_subagent_depth_limit_stays_independent_of_concurrency() -> None:
    with patch.object(settings, "max_concurrent_subtasks", 18):
        stats = SubagentManager().get_stats()
    assert stats["depth_limit"] == 3
    assert stats["concurrency_limit"] == 18
    assert SubagentManager(depth_limit=1).get_stats()["depth_limit"] == 1


def test_configured_value_reaches_every_consumer() -> None:
    with patch.object(settings, "max_concurrent_subtasks", 18):
        assert TaskManager().max_workers == 18
        assert _group_engine()._max_concurrent == 18
        assert SubagentManager().get_stats()["concurrency_limit"] == 18


def test_clamped_ceiling_reaches_task_manager() -> None:
    ceiling = _make_settings(max_concurrent_subtasks=100).max_concurrent_subtasks
    assert TaskManager(max_workers=ceiling).max_workers == 18


@pytest.mark.asyncio
@pytest.mark.parametrize("limit", [1, 2, 3, 18])
async def test_task_manager_never_exceeds_configured_concurrency(limit: int) -> None:
    manager = TaskManager(max_workers=limit)
    total = limit * 3
    assert await _measure_task_manager(manager, total) == limit


@pytest.mark.asyncio
async def test_task_manager_uses_full_default_capacity() -> None:
    manager = TaskManager()
    assert await _measure_task_manager(manager, 9) == 3


@pytest.mark.asyncio
@pytest.mark.parametrize("limit", [1, 2, 18])
async def test_subagent_manager_never_exceeds_configured_concurrency(limit: int) -> None:
    manager = SubagentManager(concurrency_limit=limit)
    assert await _measure_subagent_manager(manager, limit * 3) == limit
    assert manager.get_stats()["concurrency_limit"] == limit


@pytest.mark.asyncio
async def test_subagent_manager_runs_every_spawned_task() -> None:
    manager = SubagentManager(concurrency_limit=2)
    records = await asyncio.gather(
        *(
            manager.spawn(SubagentSpec(description=f"task-{index}"), _ok_runner)
            for index in range(6)
        )
    )
    assert [record.state.value for record in records] == ["completed"] * 6
    assert manager.get_stats()["states"]["completed"] == 6


async def _ok_runner(_spec: SubagentSpec) -> tuple[str, SubagentUsage]:
    return "done", SubagentUsage()
